# Phase 3 — Meditron-7B Fine-Tuning

## Summary

Fine-tune Meditron-7B on hospital-specific Text-to-SQL pairs using QLoRA on SageMaker.
Deploy as a SageMaker endpoint with HuggingFace TGI. This becomes the fast, cheap
inference path for simple SQL queries in Phase 4.

**Duration:** 7–10 weeks  
**Status:** Not started  
**Depends on:** Phase 0 (UC-0.5 LLMProvider, UC-0.4 SQLQueryEngine decomposed)  
**Blocks:** Phase 4 (inference routing)

---

## Training Config

| Parameter         | Value                                              |
|-------------------|----------------------------------------------------|
| Base model        | Meditron-7B (HuggingFace: `epfl-llm/meditron-7b`) |
| Instance          | `ml.g5.2xlarge` (1× A10G, 24GB VRAM) ~$1.20/hr   |
| Technique         | QLoRA (NF4 4-bit quantization)                     |
| LoRA rank         | 16, alpha=32                                       |
| Batch size        | 4, gradient accumulation=4                         |
| Gradient checkpointing | Enabled                                       |
| Epochs            | 3                                                  |
| Training duration | ~4–6 hours                                        |
| Experiment tracking | SageMaker Experiments (MLflow API)               |

---

## Dataset Format

```json
{
  "instruction": "How many patients over 65 with diabetes were admitted in Q1 2024?",
  "schema": "TABLE patient_details (registry_id INT PK, age INT, diagnosis TEXT, admission_date DATE, ...)",
  "output": "SELECT COUNT(DISTINCT p.registry_id) FROM patient_details p WHERE p.age > 65 AND p.diagnosis ILIKE '%diabetes%' AND p.admission_date BETWEEN '2024-01-01' AND '2024-03-31'"
}
```

**Target size:** 500–1000 JSONL pairs  
**Storage:** `s3://hdc-{env}-training-data/meditron/train.jsonl`  
**No real PII** — synthetic or anonymised patient data only

---

## Use Cases

### UC-3.1 — Training Dataset Construction

**Goal:** Build 500–1000 high-quality Text-to-SQL JSONL pairs covering the hospital schema.

**Tasks:**
1. Define query categories:
   - Simple count queries (1 table, 1 filter)
   - Aggregation queries (GROUP BY, HAVING)
   - Multi-table joins (2–3 tables)
   - Date range filters
   - Admission/discharge patterns
   - Diagnosis cohort queries
2. Write 50–100 seed examples manually
3. Use Claude 3.5 Sonnet to generate variations (with schema context)
4. Validate each generated SQL against dev RDS (execution check)
5. Filter out invalid / non-executing SQL
6. Split: 80% train / 20% validation
7. Upload to S3: `s3://hdc-{env}-training-data/meditron/`

**Files:**
- New: `scripts/build_training_dataset.py`
- New: `scripts/validate_sql_dataset.py`

**Done when:** 500+ validated JSONL pairs in S3; validation split SQL accuracy ≥ 75%.

---

### UC-3.2 — Terraform: meditron Module

**Goal:** Provision SageMaker training job template, model registry, and endpoint.

**Tasks:**
1. Create `modules/meditron/main.tf`:
   - `aws_sagemaker_training_job` resource (or training job template)
   - `aws_sagemaker_model` referencing HuggingFace TGI container
   - `aws_sagemaker_endpoint_configuration` (ml.g5.xlarge, scale-to-zero)
   - `aws_sagemaker_endpoint`
   - SageMaker Model Registry group: `meditron-text-to-sql`
2. IAM: SageMaker execution role with S3 read (training data + model artifacts) + ECR pull
3. Container: `763104351884.dkr.ecr.{region}.amazonaws.com/huggingface-pytorch-tgi-inference:latest`
4. Outputs: `endpoint_name`, `model_registry_arn`

**Files:**
- New: `modules/meditron/main.tf`, `variables.tf`, `outputs.tf`

**Done when:** `terraform apply` provisions endpoint in `InService` state.

---

### UC-3.3 — QLoRA Training Script

**Goal:** Implement the SageMaker training script using `transformers`, `peft`, and
`trl` (SFTTrainer).

**Tasks:**
1. Write `train.py` (SageMaker entry point):
   ```python
   from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
   from transformers import AutoModelForCausalLM, BitsAndBytesConfig
   from trl import SFTTrainer
   # load NF4 quantised Meditron-7B
   # apply LoRA (rank=16, alpha=32, target_modules=["q_proj","v_proj"])
   # train with SFTTrainer on JSONL dataset
   # save adapter to /opt/ml/model/
   ```
2. Merge adapter with base model post-training (full weights for TGI serving)
3. Log metrics to SageMaker Experiments via `smexperiments`
4. Register best checkpoint in SageMaker Model Registry with metadata:
   - `sql_accuracy`, `val_loss`, `training_dataset_size`
5. Unit test data loading + tokenisation (no GPU required)

**Files:**
- New: `hospital-data-chatbot-ml/training/meditron/train.py`
- New: `hospital-data-chatbot-ml/training/meditron/requirements.txt`
- Update: `hospital-data-chatbot-ml/scripts/train_deploy_model.py` (add Meditron job launcher)

**Done when:** Training job completes on SageMaker; model registered with `sql_accuracy ≥ 0.75`.

---

### UC-3.4 — MeditronProvider Implementation

**Goal:** Implement the `MeditronProvider` that was stubbed in Phase 0 (UC-0.5).

**Tasks:**
1. Implement `app/core/meditron_provider.py`:
   ```python
   class MeditronProvider:
       async def generate(self, prompt: str, **kwargs) -> str:
           response = sagemaker_runtime.invoke_endpoint(
               EndpointName=self.endpoint_name,
               ContentType="application/json",
               Body=json.dumps({"inputs": prompt, "parameters": {...}})
           )
           return json.loads(response["Body"].read())["generated_text"]
   ```
2. Parse TGI response format (may differ from Bedrock response shape)
3. Add `LLM_PROVIDER=meditron` to `settings.py` provider routing
4. Integration test against deployed SageMaker endpoint

**Files:**
- Update: `app/core/meditron_provider.py` (was stub `NotImplementedError`)
- `app/config/settings.py`

**Done when:** `LLM_PROVIDER=meditron` routes SQL generation to Meditron endpoint;
simple query returns valid SQL.

---

### UC-3.5 — GitHub Actions: Training Trigger

**Goal:** Add a workflow that can trigger a Meditron training job from CI.

**Tasks:**
1. Update `.github/workflows/model-training.yml`:
   - Manual trigger (`workflow_dispatch`) with `dataset_version` input
   - Launches SageMaker training job via `boto3`
   - Polls for completion (or notifies via CloudWatch Event)
   - On success: registers model in SageMaker Model Registry

**Files:**
- Update: `.github/workflows/model-training.yml`

**Done when:** Manual workflow dispatch triggers training job in AWS.

---

## Phase 3 Exit Criteria

- [ ] 500+ JSONL training pairs in S3 (all SQL validated against dev RDS)
- [ ] Training job completes on `ml.g5.2xlarge` in < 6 hours
- [ ] Model registered in SageMaker Model Registry with `sql_accuracy ≥ 0.75`
- [ ] `MeditronProvider` implements `LLMProvider` protocol
- [ ] SageMaker endpoint `InService` and reachable from ECS VPC
- [ ] GitHub Actions training trigger works
