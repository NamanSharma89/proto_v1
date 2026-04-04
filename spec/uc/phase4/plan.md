# Phase 4 — Inference Routing + Evaluation

## Summary

Wire Meditron-7B and Claude 3.5 Sonnet into a complexity-based routing decision in the
Step Functions pipeline. Build the evaluation framework to measure SQL accuracy,
hallucination rate, and latency against a benchmark dataset.

**Duration:** 10–13 weeks  
**Status:** Not started  
**Depends on:** Phase 1 (Step Functions), Phase 2 (RAG), Phase 3 (Meditron endpoint)

---

## Routing Logic

Implemented as a Step Functions **Choice state** inserted between `GenerateSQL` and
the rest of the SQL sub-pipeline:

```
simple query  (complexity_score < 0.6, ≤ 2 tables)  ──► Meditron endpoint
complex query (complexity_score ≥ 0.6, multi-join)   ──► Bedrock Claude 3.5 Sonnet
low confidence from Meditron                          ──► escalate to Claude (fallback)
document retrieval                                    ──► Bedrock Knowledge Base
hybrid                                                ──► Parallel (SQL + RAG)
```

**Complexity scoring inputs:**
- Number of tables referenced in question
- Presence of aggregation keywords (GROUP BY, HAVING, UNION)
- Date range complexity
- Subquery indicators

---

## Use Cases

### UC-4.1 — Complexity Scorer

**Goal:** Score an incoming natural language query to determine routing target.

**Tasks:**
1. Implement `app/core/complexity_scorer.py`:
   - Keyword-based scoring (fast, no LLM call)
   - Returns `{"score": float, "table_count": int, "has_aggregation": bool}`
2. Add `classify_complexity` Lambda handler for Step Functions
3. Unit test with known-simple and known-complex queries from benchmark dataset

**Scoring heuristic (v1):**
```
score = 0.0
score += 0.3 if table_count >= 3
score += 0.2 if table_count == 2
score += 0.2 if has_aggregation
score += 0.1 if has_date_range
score += 0.2 if has_subquery_keywords
```

**Files:**
- New: `app/core/complexity_scorer.py`
- New: `modules/step_functions/lambdas/classify_complexity/handler.py`

**Done when:** Scorer correctly classifies 90%+ of benchmark queries as simple/complex.

---

### UC-4.2 — Inference Router in Step Functions

**Goal:** Update the Step Functions ASL to route to Meditron vs. Claude based on
complexity score.

**Tasks:**
1. Insert `ClassifyComplexity` state after `RetrieveSchema`
2. Add `RouteByComplexity` Choice state:
   ```json
   {
     "Type": "Choice",
     "Choices": [
       {
         "Variable": "$.complexity.score",
         "NumericLessThan": 0.6,
         "Next": "GenerateSQL_Meditron"
       }
     ],
     "Default": "GenerateSQL_Claude"
   }
   ```
3. Add `GenerateSQL_Meditron` state (calls Meditron endpoint)
4. Add confidence check after Meditron: if `confidence < 0.7` → fallback to Claude
5. Merge both paths back into `ValidateSQL`

**Files:**
- Update: Step Functions ASL definition
- Update: `modules/step_functions/main.tf`

**Done when:** Simple queries route to Meditron; complex queries route to Claude;
fallback triggers on low Meditron confidence.

---

### UC-4.3 — Benchmark Dataset

**Goal:** Build a 200+ query benchmark dataset for automated evaluation.

**Dataset format:**
```json
{
  "id": "bench_001",
  "question": "How many patients over 65 were admitted in Q1 2024?",
  "expected_sql": "SELECT COUNT(DISTINCT registry_id) FROM ...",
  "expected_result_shape": {"type": "count", "column": "count"},
  "complexity": "simple",
  "tags": ["count", "age_filter", "date_range"]
}
```

**Tasks:**
1. Curate 200+ questions across all complexity levels and intent types
2. Write reference SQL for each (validated against dev RDS)
3. Upload to `s3://hdc-{env}-benchmarks/benchmark_v1.jsonl`
4. Categorise: `simple_sql`, `complex_sql`, `rag`, `hybrid`, `out_of_scope`

**Files:**
- New: `scripts/build_benchmark_dataset.py`
- New: `s3://hdc-{env}-benchmarks/benchmark_v1.jsonl` (S3, not in repo)

**Done when:** 200+ validated benchmark entries in S3.

---

### UC-4.4 — Evaluation Framework

**Goal:** Run automated evaluation of the full pipeline against the benchmark dataset.

**Metrics:**

| Metric                 | Method                                                        |
|------------------------|---------------------------------------------------------------|
| SQL Execution Accuracy | Compare result rows to expected result (exact + fuzzy match)  |
| Hallucination Rate     | LLM-as-Judge: Claude judges if response is grounded in data   |
| LLM-as-Judge approval  | Claude rates response quality 1–5, target avg ≥ 4.25         |
| Latency P50/P95        | CloudWatch metrics from Step Functions execution history      |

**Tasks:**
1. Implement `scripts/run_evaluation.py`:
   - Reads `benchmark_v1.jsonl` from S3
   - For each entry: sends request to FastAPI, records response + latency
   - Computes SQL accuracy (execute both expected and actual SQL, compare results)
   - Calls LLM-as-Judge prompt for hallucination + quality scoring
   - Writes results to `s3://hdc-{env}-benchmarks/eval_{timestamp}.json`
2. Add ECS scheduled task (EventBridge, weekly) to run evaluation
3. CloudWatch dashboard: accuracy, hallucination rate, latency P50/P95

**Files:**
- New: `scripts/run_evaluation.py`
- New: `scripts/llm_judge.py` (judge prompt + Bedrock call)
- Update: `modules/etl/main.tf` (add evaluation ECS task)

**Done when:** Evaluation run completes; results in S3; dashboard shows all 5 metrics.

---

### UC-4.5 — Evaluation Targets

| Metric                 | Baseline | Target |
|------------------------|----------|--------|
| SQL Execution Accuracy | 68%      | 82%    |
| Hallucination Rate     | baseline | -30%   |
| LLM-as-Judge approval  | —        | >85%   |
| Latency P50            | —        | <3s    |
| Latency P95            | —        | <8s    |

If targets are not met, iterate:
- SQL accuracy gap → more training data or prompt tuning
- Hallucination → tighter RAG retrieval or system prompt constraints
- Latency → Redis cache hit rate, Meditron routing ratio

---

## Phase 4 Exit Criteria

- [ ] Complexity scorer deployed and routing correctly (90%+ classification accuracy)
- [ ] Step Functions routes simple → Meditron, complex → Claude
- [ ] Meditron fallback to Claude works on low confidence
- [ ] 200+ benchmark entries in S3
- [ ] Evaluation script runs end-to-end; results written to S3
- [ ] SQL Execution Accuracy ≥ 82%
- [ ] Hallucination Rate reduced ≥ 30% vs. baseline
- [ ] LLM-as-Judge approval > 85%
- [ ] Latency P50 < 3s, P95 < 8s
- [ ] CloudWatch dashboard shows all evaluation metrics
