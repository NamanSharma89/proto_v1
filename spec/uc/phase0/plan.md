# Phase 0 — Foundation Fixes

## Summary

Critical prerequisite for all other phases. Addresses security vulnerabilities, a broken
AWS configuration, a monolithic class that blocks decomposition, and a schema that
forces hacky SQL workarounds. Nothing in Phase 1+ is safe to build until these are done.

**Duration:** 1–2 weeks  
**Status:** Not started  
**Blocks:** All phases

---

## Use Cases

### UC-0.1 — Database Schema Migration

**Problem:** All RDS PostgreSQL columns are TEXT. Every SQL query requires CAST/NULLIF
workarounds, which pollute LLM prompts and cause silent type errors.

**Goal:** Migrate to proper column types so queries work naturally.

**Tasks:**
1. Audit all tables — identify columns that should be `INTEGER`, `NUMERIC`, `DATE`, `BOOLEAN`
2. Set up Alembic in `hospital-data-chatbot/` with `alembic init`
3. Write migration: convert TEXT columns to typed equivalents (handle nulls)
4. Test migration on dev DB with existing data
5. Update Pydantic models in `app/models/data_models.py` to match new types
6. Remove all CAST/NULLIF hacks from LLM prompt templates in `sql_query_engine.py`

**Affected files:**
- `app/models/data_models.py`
- `app/core/sql_query_engine.py`
- New: `alembic/` directory + migration scripts

**Done when:** `alembic upgrade head` runs cleanly on dev; no CAST/NULLIF in prompts.

---

### UC-0.2 — Fix SQL Injection Vulnerability

**Problem:** `ml_routes.py` ~line 123 interpolates `patient_id` directly into an SQL
f-string. This is a critical security vulnerability.

**Goal:** Replace with parameterised query.

**Tasks:**
1. Locate the f-string SQL in `hospital-data-chatbot-ml/` routes
2. Replace with `psycopg2` parameterised query (`%s` placeholders, tuple params)
3. Audit remaining routes for any other string-interpolated SQL
4. Add input validation for `patient_id` (type check, range check)

**Affected files:**
- `hospital-data-chatbot-ml/` (routes file with SQL injection)

**Done when:** No f-string SQL in codebase; `bandit` scan returns no SQL injection warnings.

---

### UC-0.3 — Fix Bedrock IAM + Model ARN

**Problem:** `modules/bedrock/main.tf` points to a Titan model ARN instead of Claude.
IAM policy may also be over-scoped or incorrectly scoped.

**Goal:** Correct model ID and tighten IAM.

**Tasks:**
1. Open `hospital-data-chatbot-infrastructure/deploy/terraform/modules/bedrock/main.tf`
2. Replace Titan model ARN with `anthropic.claude-3-5-sonnet-20241022-v2:0`
3. Verify IAM policy allows `bedrock:InvokeModel` on the correct model ARN only
4. Run `terraform plan` in dev environment to confirm no destructive changes
5. Apply in `dev` first, validate API response, then promote to `dev-cloud`

**Affected files:**
- `modules/bedrock/main.tf`
- `modules/bedrock/variables.tf`

**Done when:** `terraform apply` succeeds; API returns Claude response (not Titan error).

---

### UC-0.4 — Decompose SQLQueryEngine

**Problem:** `app/core/sql_query_engine.py` is ~750 lines doing schema retrieval, SQL
generation, validation, execution, and result formatting — all in one class. This blocks
Step Functions decomposition and makes testing near-impossible.

**Goal:** Extract into 5 focused classes, each independently testable.

**New classes:**

| Class             | Responsibility                                          | File                          |
|-------------------|---------------------------------------------------------|-------------------------------|
| `SchemaRetriever` | Fetch table schemas (Redis cache + DB fallback)         | `core/schema_retriever.py`    |
| `SQLGenerator`    | Build SQL prompt + call LLM, return raw SQL string      | `core/sql_generator.py`       |
| `SQLValidator`    | Parse + validate SQL (syntax, table names, injections)  | `core/sql_validator.py`       |
| `SQLExecutor`     | Execute SQL against RDS, return raw rows                | `core/sql_executor.py`        |
| `ResultFormatter` | Format rows into human-readable response                | `core/result_formatter.py`    |

**Tasks:**
1. Write unit tests for each class boundary (test-first)
2. Extract `SchemaRetriever` — currently inline in `sql_query_engine.py`
3. Extract `SQLGenerator` — prompt building + Bedrock call
4. Extract `SQLValidator` — regex/AST checks currently scattered
5. Extract `SQLExecutor` — psycopg2 execution block
6. Extract `ResultFormatter` — response shaping
7. Replace `SQLQueryEngine` body with calls to the 5 new classes (facade pattern)
8. Verify all existing API tests pass

**Affected files:**
- `app/core/sql_query_engine.py` (refactored to facade)
- New: `app/core/schema_retriever.py`, `sql_generator.py`, `sql_validator.py`,
  `sql_executor.py`, `result_formatter.py`

**Done when:** All 5 classes have unit tests; `SQLQueryEngine` is a thin orchestrator;
no test regressions.

---

### UC-0.5 — Extract LLMProvider Protocol

**Problem:** `app/core/llm_connector.py` and `ollama_connector.py` are concrete
implementations with no shared interface. Adding Meditron requires forking logic across
multiple call sites.

**Goal:** Define an `LLMProvider` protocol; make Bedrock, Ollama, and future Meditron
endpoint implement it.

**Interface:**
```python
class LLMProvider(Protocol):
    async def generate(self, prompt: str, **kwargs) -> str: ...
    async def generate_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
```

**Tasks:**
1. Define `LLMProvider` protocol in `app/core/llm_provider.py`
2. Refactor `BedrockLLM` to implement the protocol
3. Refactor `OllamaConnector` to implement the protocol
4. Add stub `MeditronProvider` (raises `NotImplementedError` — implemented in Phase 3)
5. Update `SQLGenerator` (UC-0.4) to accept `LLMProvider` via dependency injection
6. Update `app/config/settings.py` to select provider based on env var (`LLM_PROVIDER`)

**Affected files:**
- New: `app/core/llm_provider.py`
- `app/core/llm_connector.py`
- `app/core/ollama_connector.py`
- `app/core/sql_generator.py`
- `app/config/settings.py`

**Done when:** Switching `LLM_PROVIDER=ollama` vs `LLM_PROVIDER=bedrock` routes to the
correct implementation without code changes; protocol mypy-checked.

---

## Phase 0 Exit Criteria

- [ ] Alembic migration applied to dev DB; no CAST/NULLIF in prompts
- [ ] No f-string SQL anywhere in codebase (`bandit` clean)
- [ ] Bedrock module points to Claude 3.5 Sonnet ARN; `terraform apply` succeeds
- [ ] `SQLQueryEngine` decomposed into 5 classes; all have unit tests
- [ ] `LLMProvider` protocol defined; Bedrock + Ollama implementations passing tests
- [ ] All existing integration tests green
