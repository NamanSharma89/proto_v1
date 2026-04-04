# Healthcare Analytics Platform — Roadmap

## Vision

Upgrade the hospital data chatbot from a direct boto3/LLM chain into a production-grade
healthcare analytics platform with agentic orchestration, RAG over clinical documents,
and a fine-tuned medical SQL model.

---

## Phase Overview

| Phase | Name                          | Duration    | Status     | Blocks         |
|-------|-------------------------------|-------------|------------|----------------|
| 0     | Foundation Fixes              | 1–2 weeks   | Not started | All phases     |
| 1     | Step Functions Pipeline       | 3–5 weeks   | Not started | Phase 2, 4     |
| 2     | Bedrock Knowledge Bases (RAG) | 5–7 weeks   | Not started | Phase 4        |
| 3     | Meditron-7B Fine-Tuning       | 7–10 weeks  | Not started | Phase 4        |
| 4     | Inference Routing + Evaluation| 10–13 weeks | Not started | —              |
| 5     | High-Performance ETL          | Parallel w/ 4 | Not started | —            |

---

## Architecture Target

```
User Query
    │
    v
FastAPI (ECS Fargate)
    │
    v
AWS Step Functions ─── intent classifier ──► RouteByIntent
    │                   (Bedrock Claude)         │
    │                                     ┌──────┴──────────────┐
    │                                     │         │            │
    v                                     v         v            v
SQL Sub-Pipeline              RAG Pipeline      Hybrid (Parallel)
  │                         (Bedrock KB +         SQL + RAG
  ├── Schema Retriever        OpenSearch          merged by LLM
  │   (ElastiCache Redis)     Serverless)
  │
  ├── Route by Complexity
  │     simple ──► Meditron-7B (SageMaker)
  │     complex ──► Claude 3.5 Sonnet (Bedrock)
  │
  ├── SQL Validator
  ├── SQL Executor (RDS PostgreSQL)
  └── Rewrite Loop (max 3 retries)
```

---

## Component Migration Plan

| Status | Component                                          | Action                                      |
|--------|----------------------------------------------------|---------------------------------------------|
| ✅ Keep | Terraform modules (networking, ECS, ALB, RDS, S3) | Keep as-is                                  |
| ✅ Keep | CI/CD (GitHub Actions OIDC + ECR + ECS)            | Keep                                        |
| ✅ Keep | FastAPI shell, Polars ETL                          | Keep, extend                                |
| ✅ Keep | MCP protocol Pydantic models                       | Keep                                        |
| 🔄 Refactor | BedrockLLM → LLMProvider protocol             | Add Meditron + structured output            |
| 🔄 Refactor | SQLQueryEngine (750 lines)                    | Decompose into 5 classes                    |
| 🔄 Refactor | SageMakerIntegration                          | Extend for Meditron QLoRA fine-tuning       |
| 🔄 Refactor | FeatureStore (Parquet files)                  | Migrate to SageMaker Feature Store          |
| 🔄 Fix      | Bedrock Terraform module                      | Fix wrong model ARN (Titan → Claude)        |
| ❌ Remove   | All-TEXT database schema                      | Migrate to proper types                     |
| 🆕 New      | Step Functions state machine                  | New                                         |
| 🆕 New      | Bedrock Knowledge Bases + OpenSearch Serverless | New                                       |
| 🆕 New      | Meditron-7B QLoRA fine-tuning pipeline        | New                                         |
| 🆕 New      | Inference router (complexity-based)           | New                                         |
| 🆕 New      | Evaluation framework                          | New                                         |
| 🆕 New      | ElastiCache Redis (schema cache)              | New                                         |

---

## New Terraform Modules Required

```
modules/
  knowledge_base/     # Bedrock KB, OpenSearch Serverless, S3 data source
  step_functions/     # State machine + Lambda functions
  elasticache/        # Redis for schema caching
  etl/                # ECS scheduled task + EventBridge rule
  feature_store/      # SageMaker Feature Store feature groups
  meditron/           # Training job template, endpoint, model registry
```

---

## Estimated Monthly AWS Cost (dev-cloud)

| Service                                      | Est.         |
|----------------------------------------------|--------------|
| OpenSearch Serverless (2 OCU min)            | ~$350        |
| SageMaker Meditron endpoint (scale-to-zero)  | ~$80         |
| Bedrock Claude (50K tokens/day)              | ~$45         |
| ECS + RDS + Redis + Lambda                   | ~$65         |
| S3 + CloudWatch + Step Functions             | ~$15         |
| **Total dev-cloud**                          | **~$555/mo** |

> OpenSearch Serverless is the dominant cost. pgvector on RDS can substitute initially
> if budget is constrained (lower retrieval quality, no minimum cost).

---

## Evaluation Targets (Phase 4)

| Metric                 | Baseline | Target |
|------------------------|----------|--------|
| SQL Execution Accuracy | 68%      | 82%    |
| Hallucination Rate     | baseline | -30%   |
| LLM-as-Judge approval  | —        | >85%   |
| Latency P50            | —        | <3s    |
| Latency P95            | —        | <8s    |

Benchmark dataset: 200+ test cases in S3 (`benchmark_v1.jsonl`), run via scheduled ECS task.
