# Healthcare Analytics Platform — Planned Tech Stack

## API Layer

| Component      | Current                  | Planned                        |
|----------------|--------------------------|--------------------------------|
| Framework      | FastAPI                  | FastAPI (keep)                 |
| Runtime        | Python 3.12+             | Python 3.12+ (keep)            |
| Hosting        | ECS Fargate              | ECS Fargate (keep)             |
| Load Balancer  | ALB                      | ALB (keep)                     |
| Orchestration  | Direct boto3 LLM calls   | AWS Step Functions (Express)   |

---

## LLM / AI

| Component             | Current                             | Planned                                        |
|-----------------------|-------------------------------------|------------------------------------------------|
| Primary LLM           | Bedrock Claude 3 Sonnet (outdated ID) | Bedrock Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`) |
| Local dev LLM         | Ollama                              | Ollama (keep)                                  |
| Medical SQL model     | None                                | Meditron-7B (SageMaker endpoint, HuggingFace TGI) |
| Fine-tuning           | None                                | QLoRA on SageMaker (ml.g5.2xlarge)             |
| Embedding model       | None                                | `amazon.titan-embed-text-v2:0` (1024d)         |
| Intent classification | None                                | Bedrock Claude (Step Functions first state)    |

---

## Data / Storage

| Component       | Current                    | Planned                                   |
|-----------------|----------------------------|-------------------------------------------|
| Primary DB      | RDS PostgreSQL (all-TEXT)  | RDS PostgreSQL (typed schema + Alembic)   |
| Schema cache    | None                       | ElastiCache Redis                         |
| Feature store   | S3 Parquet files           | SageMaker Feature Store                   |
| Vector store    | None                       | OpenSearch Serverless (Phase 2)           |
| Document store  | None                       | S3 + Bedrock Knowledge Bases              |
| Migrations      | None                       | Alembic                                   |

---

## ML Platform

| Component             | Current                       | Planned                                        |
|-----------------------|-------------------------------|------------------------------------------------|
| Training              | SageMaker (XGBoost)           | SageMaker (QLoRA fine-tuning + Experiments)    |
| Inference             | SageMaker endpoint            | SageMaker endpoint (HuggingFace TGI, scale-to-zero) |
| Inference routing     | None                          | Step Functions Choice state (complexity-based) |
| Experiment tracking   | None                          | SageMaker Experiments (MLflow API)             |
| Model registry        | None                          | SageMaker Model Registry                       |

---

## Retrieval-Augmented Generation (RAG)

| Component        | Current | Planned                                         |
|------------------|---------|--------------------------------------------------|
| Knowledge base   | None    | Bedrock Knowledge Bases                          |
| Chunking         | None    | Semantic chunking (clinical section boundaries)  |
| Vector store     | None    | OpenSearch Serverless (~$350/mo minimum)          |
| Retrieval API    | None    | `bedrock-agent-runtime.retrieve_and_generate()`  |
| Fallback option  | N/A     | pgvector on RDS (lower cost, lower quality)      |

---

## ETL / Data Pipeline

| Component        | Current               | Planned                                    |
|------------------|-----------------------|--------------------------------------------|
| ETL framework    | Polars                | Polars lazy pipeline (keep, extend)        |
| Scheduling       | Manual / ad-hoc       | EventBridge rule (02:00 UTC daily)         |
| ETL hosting      | Local / ECS           | ECS scheduled task (4 vCPU / 16GB)        |
| Rejected records | Dropped               | Written to S3 for review                   |

---

## Infrastructure (Terraform)

| Module              | Current | Planned                                  |
|---------------------|---------|------------------------------------------|
| networking          | ✅      | Keep                                     |
| app_deployment      | ✅      | Keep                                     |
| database            | ✅      | Keep (schema migration separate)         |
| storage             | ✅      | Keep                                     |
| monitoring          | ✅      | Keep                                     |
| bedrock             | ⚠️ Fix  | Fix model ARN (Titan → Claude)           |
| sagemaker           | 🔄      | Extend for Meditron training + endpoint  |
| ml_api              | ✅      | Keep                                     |
| **step_functions**  | 🆕 New  | State machine + Lambda functions         |
| **knowledge_base**  | 🆕 New  | Bedrock KB + OpenSearch Serverless       |
| **elasticache**     | 🆕 New  | Redis for schema caching                 |
| **etl**             | 🆕 New  | ECS scheduled task + EventBridge         |
| **feature_store**   | 🆕 New  | SageMaker Feature Store feature groups   |
| **meditron**        | 🆕 New  | Training job template + endpoint         |

---

## CI/CD

| Component        | Current                           | Planned                              |
|------------------|-----------------------------------|--------------------------------------|
| Pipeline         | GitHub Actions                    | GitHub Actions (keep)                |
| Auth             | OIDC → AWS IAM                   | OIDC → AWS IAM (keep)                |
| Image registry   | ECR                               | ECR (keep)                           |
| Deployment       | ECS rolling update                | ECS rolling update (keep)            |
| ML training      | `model-training.yml` workflow     | Extend for Meditron fine-tune trigger |

---

## Security Fixes Required (Phase 0)

- `ml_routes.py` ~line 123: f-string SQL with `patient_id` → parameterized query
- `modules/bedrock/main.tf`: wrong model ARN (Titan) → correct Claude ARN + IAM scope
- All-TEXT RDS schema → typed columns, eliminates CAST/NULLIF hacks in prompts
