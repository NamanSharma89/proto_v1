# Phase 1 — Step Functions Pipeline

## Summary

Replace the direct FastAPI → LLM call chain with an AWS Step Functions Express Workflow.
This introduces intent classification, parallel routing, and the SQL rewrite loop as
durable, observable state machine steps.

**Duration:** 3–5 weeks  
**Status:** Not started  
**Depends on:** Phase 0 (all UCs)  
**Blocks:** Phase 2 (RAG branch), Phase 4 (routing)

---

## State Machine Design

```
ClassifyIntent
    │
    v
RouteByIntent (Choice state)
    ├── intent = "sql"     ──► SQL Sub-Pipeline
    ├── intent = "rag"     ──► RAG Pipeline (Phase 2 — stub in Phase 1)
    ├── intent = "hybrid"  ──► Parallel (SQL + RAG)
    └── intent = "other"   ──► FormatError
    │
    v
FormatResponse
```

**SQL Sub-Pipeline (nested state machine):**
```
RetrieveSchema → GenerateSQL → ValidateSQL → ExecuteSQL
                                    ↑               ↓ on failure
                                RewriteSQL ◄────────┘  (max 3 loops)
```

FastAPI calls `sfn_client.start_sync_execution()` — synchronous Express Workflow,
returns full execution result inline.

---

## Use Cases

### UC-1.1 — Terraform: step_functions Module

**Goal:** Provision the Step Functions state machine and all supporting Lambda functions.

**Tasks:**
1. Create `modules/step_functions/main.tf`
2. Define Express Workflow state machine (ASL JSON/YAML)
3. Create 7 Lambda functions (one per state):
   - `classify_intent` — calls Bedrock Claude with intent classification prompt
   - `retrieve_schema` — calls Redis cache via `SchemaRetriever` (Phase 0)
   - `generate_sql` — calls `SQLGenerator` (Phase 0)
   - `validate_sql` — calls `SQLValidator` (Phase 0)
   - `execute_sql` — calls `SQLExecutor` (Phase 0)
   - `rewrite_sql` — calls `SQLGenerator` with error context + retry counter
   - `format_response` — calls `ResultFormatter` (Phase 0)
4. IAM roles: Step Functions execution role + per-Lambda roles (least privilege)
5. State machine error handling: retry policies, catch blocks → FormatError state
6. Outputs: state machine ARN

**Files:**
- New: `modules/step_functions/main.tf`, `variables.tf`, `outputs.tf`
- New: `modules/step_functions/lambdas/` (7 × Python Lambda handlers)

**Done when:** `terraform apply` provisions state machine; manual test execution succeeds.

---

### UC-1.2 — Lambda Handlers

**Goal:** Implement each Lambda handler as a thin wrapper around Phase 0 service classes.

**Each Lambda:**
- Receives Step Functions input (JSON event)
- Calls the relevant service class
- Returns structured output for the next state

**Rewrite loop logic (`rewrite_sql`):**
```python
retry_count = event.get("retry_count", 0)
if retry_count >= 3:
    raise MaxRetriesExceeded("SQL rewrite limit reached")
# call SQLGenerator with original query + error message
return {"sql": new_sql, "retry_count": retry_count + 1}
```

**Tasks:**
1. Write handler for each of the 7 Lambda functions
2. Define input/output JSON schema per state (used in ASL `Parameters` + `ResultSelector`)
3. Package shared service classes as a Lambda layer
4. Unit test each handler with mock Step Functions events

**Files:**
- New: `modules/step_functions/lambdas/{classify_intent,retrieve_schema,generate_sql,
  validate_sql,execute_sql,rewrite_sql,format_response}/handler.py`
- New: `modules/step_functions/lambdas/shared_layer/` (Phase 0 service classes)

**Done when:** All 7 handlers have unit tests; integration test drives full SQL path.

---

### UC-1.3 — FastAPI Integration

**Goal:** Replace direct LLM call in `sql_chat_routes.py` with a Step Functions
`start_sync_execution` call.

**Tasks:**
1. Add `StepFunctionsClient` wrapper in `app/utils/aws.py`
2. Update `sql_chat_routes.py` POST handler:
   - Build input payload: `{"query": query, "user_id": user_id}`
   - Call `sfn_client.start_sync_execution(stateMachineArn=..., input=json.dumps(payload))`
   - Parse execution output, return response
3. Add `STATE_MACHINE_ARN` to `app/config/settings.py` (from env var)
4. Handle Step Functions failure states (execution timed out, task failed)
5. Update integration tests to mock `start_sync_execution`

**Files:**
- `app/api/sql_chat_routes.py`
- `app/utils/aws.py`
- `app/config/settings.py`

**Done when:** End-to-end request through FastAPI → Step Functions → SQL → response works
in dev environment.

---

### UC-1.4 — RAG Pipeline Stub

**Goal:** Add a `rag_pipeline` placeholder state so `RouteByIntent` can route to it
without breaking the state machine. Full implementation in Phase 2.

**Tasks:**
1. Add `rag_pipeline` Lambda that returns `{"response": "RAG not yet implemented"}`
2. Wire into `RouteByIntent` Choice state
3. Add `hybrid_pipeline` stub: runs SQL + RAG in parallel (Parallel state), returns
   merged stub response

**Done when:** Routing to `intent = "rag"` returns stub without state machine failure.

---

## Phase 1 Exit Criteria

- [ ] Step Functions state machine deployed via Terraform
- [ ] All 7 Lambda handlers implemented + unit tested
- [ ] Full SQL path (RetrieveSchema → GenerateSQL → ValidateSQL → ExecuteSQL) executes end-to-end
- [ ] Rewrite loop triggers on SQL failure, retries up to 3×, then returns error
- [ ] FastAPI routes traffic through Step Functions
- [ ] RAG + Hybrid stubs in place (no failures on routing)
- [ ] CloudWatch logs visible for all state transitions
