# Spec

Planning and design documents for the Healthcare Analytics Platform.

## Documents

| File | Description |
|------|-------------|
| [roadmap.md](roadmap.md) | Phase overview, architecture diagram, component migration table, cost estimates |
| [tech_stack.md](tech_stack.md) | Current vs. planned stack for every layer (API, LLM, data, ML, infra, CI/CD) |
| [product.md](product.md) | User personas, core capabilities, NFRs, success metrics, constraints |

## Use Cases by Phase

| Phase | Folder | Summary |
|-------|--------|---------|
| 0 | [uc/phase0/](uc/phase0/plan.md) | Foundation fixes — schema migration, SQL injection fix, Bedrock ARN, SQLQueryEngine decomposition, LLMProvider protocol |
| 1 | [uc/phase1/](uc/phase1/plan.md) | Step Functions pipeline — intent classification, SQL sub-pipeline, rewrite loop, FastAPI integration |
| 2 | [uc/phase2/](uc/phase2/plan.md) | Bedrock Knowledge Bases — OpenSearch Serverless, RAG pipeline, hybrid synthesis |
| 3 | [uc/phase3/](uc/phase3/plan.md) | Meditron-7B fine-tuning — QLoRA on SageMaker, training dataset, MeditronProvider |
| 4 | [uc/phase4/](uc/phase4/plan.md) | Inference routing + evaluation — complexity scorer, benchmark dataset, evaluation framework |
| 5 | [uc/phase5/](uc/phase5/plan.md) | High-performance ETL — scheduled Polars pipeline, SageMaker Feature Store migration |
