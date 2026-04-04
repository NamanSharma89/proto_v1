# Phase 5 — High-Performance ETL

## Summary

Productionise the Polars ETL pipeline as a scheduled ECS task. Migrates from ad-hoc
data loading to a daily automated pipeline that reads Parquet from S3, validates and
transforms data, loads into RDS, and writes rejected records back to S3 for review.

**Duration:** Parallel with Phase 4 (can start after Phase 0)  
**Status:** Not started  
**Depends on:** Phase 0 (UC-0.1 typed schema)  
**Blocks:** Nothing (independent)

---

## Pipeline Design

```python
# Polars lazy pipeline on ECS (4 vCPU / 16 GB)
(
    pl.scan_parquet("s3://hdc-{env}-raw-data/patients/*.parquet")
    .with_columns([
        pl.col("age").cast(pl.Int32),
        pl.col("admission_date").str.to_datetime(),
        pl.col("diagnosis").str.to_lowercase().str.strip_chars(),
    ])
    .filter(pl.col("registry_id").is_not_null())
    .unique(subset=["registry_id"])
    .collect()
    .write_database(
        "postgresql://...",
        table="patient_details",
        if_table_exists="append"
    )
)
```

Schedule: **EventBridge rule → ECS scheduled task**, 02:00 UTC daily  
Rejected records: written to `s3://hdc-{env}-rejected/etl_{date}.parquet`

---

## Use Cases

### UC-5.1 — Terraform: etl Module

**Goal:** Provision the ECS scheduled task, EventBridge rule, and supporting IAM.

**Tasks:**
1. Create `modules/etl/main.tf`:
   - `aws_ecs_task_definition` (ETL task, 4 vCPU / 16GB, Fargate)
   - `aws_cloudwatch_event_rule` (cron: `0 2 * * *`)
   - `aws_cloudwatch_event_target` (ECS task on the existing cluster)
   - IAM: EventBridge role to run ECS tasks; ECS task role with S3 read/write + RDS access
2. Outputs: `task_definition_arn`, `event_rule_arn`

**Files:**
- New: `modules/etl/main.tf`, `variables.tf`, `outputs.tf`

**Done when:** `terraform apply` succeeds; EventBridge rule visible in console.

---

### UC-5.2 — ETL Application

**Goal:** Implement the Polars pipeline as a standalone ECS task entrypoint.

**Tasks:**
1. Create `hospital-data-chatbot/app/etl/pipeline.py`:
   - Scan Parquet from S3 using `pl.scan_parquet` with `storage_options` (boto3 credentials)
   - Apply transformations:
     - `age` → `Int32`
     - `admission_date` → `Datetime`
     - `discharge_date` → `Datetime` (nullable)
     - `diagnosis` → lowercase + strip
     - `registry_id` → `Int64`
   - Filter: `registry_id.is_not_null()`
   - Deduplicate: `unique(subset=["registry_id"])`
2. Validation step before write:
   - Age: 0 ≤ age ≤ 130
   - `registry_id`: positive integer
   - `admission_date`: not in the future
   - Collect rejected rows → write to S3 rejected bucket
3. Write valid rows to RDS using `write_database` (append mode)
4. Log: rows processed, rows written, rows rejected, duration

**Files:**
- New: `app/etl/pipeline.py`
- New: `app/etl/validators.py`
- New: `app/etl/__init__.py`
- Update: `Dockerfile` (add ETL entrypoint, or separate Dockerfile)

**Done when:** Pipeline runs against sample S3 data; RDS row count increases correctly;
rejected records appear in S3.

---

### UC-5.3 — SageMaker Feature Store Migration

**Goal:** Replace the existing S3 Parquet feature store with SageMaker Feature Store.

**Background:** `hospital-data-chatbot-ml` currently reads/writes feature data as
Parquet files on S3. SageMaker Feature Store provides versioning, point-in-time
retrieval, and integration with SageMaker training jobs.

**Tasks:**
1. Define feature groups in `modules/feature_store/main.tf`:
   - `patient_demographics` (registry_id, age, gender, admission_date)
   - `clinical_features` (diagnosis, procedure_codes, lab_values)
2. Update `hospital-data-chatbot-ml` feature engineering to write to Feature Store:
   ```python
   feature_store_session.ingest(
       data_frame=features_df,
       feature_group_name="patient_demographics",
       max_workers=3
   )
   ```
3. Update training data loading to use Feature Store offline store (S3 backed)
4. Remove legacy Parquet feature write code from `data_processor.py`

**Files:**
- New: `modules/feature_store/main.tf`, `variables.tf`, `outputs.tf`
- Update: `hospital-data-chatbot-ml/` feature engineering scripts
- Update: `hospital-data-chatbot/app/core/data_processor.py`

**Done when:** ML training job reads features from SageMaker Feature Store; legacy
Parquet paths removed.

---

### UC-5.4 — Monitoring + Alerting

**Goal:** Instrument the ETL pipeline with CloudWatch metrics and failure alerting.

**Tasks:**
1. Emit custom CloudWatch metrics from ETL task:
   - `ETL/RowsProcessed`, `ETL/RowsWritten`, `ETL/RowsRejected`, `ETL/DurationSeconds`
2. CloudWatch alarm: `ETL/RowsRejected > 1000` → SNS → email alert
3. CloudWatch alarm: ECS task failure (task stopped with non-zero exit) → SNS
4. Log groups: `/ecs/hdc-{env}-etl` with 30-day retention

**Files:**
- Update: `app/etl/pipeline.py` (add CloudWatch `put_metric_data` calls)
- Update: `modules/etl/main.tf` (CloudWatch alarms, SNS topic)

**Done when:** After a pipeline run, CloudWatch metrics visible; alarm fires on
synthetic high-rejection test.

---

## Phase 5 Exit Criteria

- [ ] EventBridge schedules ECS ETL task at 02:00 UTC daily
- [ ] Pipeline reads Parquet from S3, validates, deduplicates, writes to RDS
- [ ] Rejected records written to S3 rejected bucket with reason column
- [ ] SageMaker Feature Store replaces S3 Parquet feature files
- [ ] CloudWatch metrics emitted per run
- [ ] Failure alert fires within 5 minutes of ECS task failure
- [ ] ETL run completes in < 15 minutes for 1M row dataset (4 vCPU / 16GB)
