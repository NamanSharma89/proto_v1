# Phase 2 — Bedrock Knowledge Bases (RAG)

## Summary

Implement the RAG pipeline for clinical document retrieval. Ingests PDFs (clinical notes,
research protocols) from S3 into Bedrock Knowledge Bases backed by OpenSearch Serverless.
Replaces the Phase 1 RAG stub with a real retrieval + synthesis pipeline.

**Duration:** 5–7 weeks  
**Status:** Not started  
**Depends on:** Phase 0 (UC-0.5 LLMProvider), Phase 1 (UC-1.4 stub in place)  
**Blocks:** Phase 4 (hybrid routing evaluation)

---

## Architecture

```
User query (intent = "rag")
    │
    v
retrieve_rag Lambda
    │
    ├── bedrock-agent-runtime.retrieve_and_generate()
    │       │
    │       ├── Embedding: amazon.titan-embed-text-v2:0 (1024d)
    │       ├── Vector store: OpenSearch Serverless
    │       └── Synthesis: Claude 3.5 Sonnet
    │
    v
FormatResponse
```

**Hybrid path:**
```
Parallel state
  ├── Branch 1: SQL Sub-Pipeline
  └── Branch 2: RAG Pipeline
        │
        v
    LLM Synthesizer (merges SQL result + RAG chunks)
```

---

## Use Cases

### UC-2.1 — Terraform: knowledge_base Module

**Goal:** Provision Bedrock Knowledge Base, OpenSearch Serverless collection, and S3
data source bucket.

**Tasks:**
1. Create `modules/knowledge_base/main.tf`:
   - `aws_opensearchserverless_collection` (type: `VECTORSEARCH`)
   - `aws_opensearchserverless_access_policy` + `aws_opensearchserverless_security_policy`
   - `aws_bedrockagent_knowledge_base` (embedding model: `amazon.titan-embed-text-v2:0`)
   - `aws_bedrockagent_data_source` (S3 bucket as source)
   - S3 bucket for clinical documents (`hdc-{env}-clinical-docs`)
2. IAM: Bedrock Knowledge Base service role with S3 read + OpenSearch write
3. Outputs: `knowledge_base_id`, `data_source_id`, `opensearch_collection_endpoint`

**Cost note:** OpenSearch Serverless minimum ~$350/mo (2 OCU). Consider gating Phase 2
behind a feature flag until budget is confirmed.

**Files:**
- New: `modules/knowledge_base/main.tf`, `variables.tf`, `outputs.tf`

**Done when:** `terraform apply` succeeds; knowledge base appears in Bedrock console.

---

### UC-2.2 — Document Ingestion Pipeline

**Goal:** Upload clinical documents to S3 and sync to Bedrock Knowledge Base.

**Ingestion config:**
- Chunking strategy: **Semantic chunking** (natural section boundaries in clinical docs)
- Source: `s3://hdc-{env}-clinical-docs/` (PDFs only)
- Sync: triggered manually or via EventBridge on S3 `PutObject`

**Tasks:**
1. Define S3 event → Lambda → `start_ingestion_job` trigger
2. Lambda handler: calls `bedrock-agent.start_ingestion_job(knowledgeBaseId=..., dataSourceId=...)`
3. Monitor ingestion job status (polling Lambda or CloudWatch Event)
4. Upload sample clinical documents (anonymised / synthetic) to validate chunking
5. Verify chunks appear in OpenSearch Serverless index

**Files:**
- New: `modules/knowledge_base/lambdas/ingest_trigger/handler.py`
- Update: `modules/knowledge_base/main.tf` (S3 event notification, ingest Lambda)

**Done when:** Document uploaded to S3 triggers ingestion; chunks searchable in KB.

---

### UC-2.3 — RAG Lambda Handler

**Goal:** Implement the `retrieve_rag` Lambda that replaces the Phase 1 stub.

**Tasks:**
1. Implement `retrieve_rag/handler.py`:
   ```python
   response = bedrock_agent_runtime.retrieve_and_generate(
       input={"text": query},
       retrieveAndGenerateConfiguration={
           "type": "KNOWLEDGE_BASE",
           "knowledgeBaseConfiguration": {
               "knowledgeBaseId": KNOWLEDGE_BASE_ID,
               "modelArn": "anthropic.claude-3-5-sonnet-20241022-v2:0",
               "retrievalConfiguration": {
                   "vectorSearchConfiguration": {"numberOfResults": 5}
               }
           }
       }
   )
   ```
2. Extract citations from response (`retrievedReferences`)
3. Return structured output: `{"response": text, "citations": [...]}`
4. Unit test with mocked `retrieve_and_generate`

**Files:**
- Update: `modules/step_functions/lambdas/retrieve_rag/handler.py` (was stub)

**Done when:** RAG path returns real response with citations for a test clinical query.

---

### UC-2.4 — Hybrid Synthesis Lambda

**Goal:** Implement the LLM synthesizer that merges SQL result + RAG chunks for hybrid
queries.

**Tasks:**
1. Implement `synthesize_hybrid/handler.py`:
   - Receives `{"sql_result": ..., "rag_result": ..., "original_query": ...}`
   - Builds synthesis prompt combining both results
   - Calls Bedrock Claude to produce unified response
2. Update Step Functions Parallel state to call this after both branches complete
3. Unit test with mock SQL + RAG inputs

**Files:**
- New: `modules/step_functions/lambdas/synthesize_hybrid/handler.py`
- Update: Step Functions ASL (add synthesizer after Parallel state)

**Done when:** Hybrid query returns a response that cites both structured data and
clinical documents.

---

## Phase 2 Exit Criteria

- [ ] OpenSearch Serverless collection + Bedrock Knowledge Base deployed via Terraform
- [ ] Clinical documents ingested and searchable
- [ ] RAG Lambda returns real responses with citations
- [ ] Hybrid path runs SQL + RAG in parallel and synthesizes result
- [ ] RAG latency P95 < 8s
- [ ] Cost validated: OpenSearch Serverless bill confirmed < $400/mo in dev-cloud
