# EvidenceGraph — Agent Implementation Specification

## 1. Purpose

EvidenceGraph is a production-style research intelligence platform for ingesting technical papers and answering multi-document questions with verifiable evidence.

The application must go beyond a basic “chat with PDF” demo. It must expose the retrieval pipeline, provide page-level citations, compare retrieval strategies, and measure retrieval and answer quality.

This document is the source of truth for implementation. When requirements conflict, follow this file unless the user explicitly changes the scope.

---

## 2. Product Goals

Build a web application that allows users to:

1. Create a research collection.
2. Upload PDF papers into that collection.
3. Track ingestion progress.
4. Ask questions across all papers in the collection.
5. Receive answers with page-level citations.
6. Open the source PDF at the cited page and highlight the supporting passage.
7. Compare selected papers in a structured table.
8. Inspect retrieved chunks and their ranking scores.
9. Compare dense, sparse, hybrid, and reranked retrieval.
10. View evaluation metrics for retrieval quality, groundedness, latency, and cost.

The final product should look like a credible internal research tool, not a notebook or tutorial project.

---

## 3. Target Users

Primary users:

- AI and machine-learning engineers
- Researchers
- Graduate students
- Technical product teams
- Recruiters reviewing the portfolio project

Primary user problem:

> Technical information is spread across many papers, and ordinary LLM answers do not make it easy to verify claims or understand why specific evidence was selected.

---

## 4. MVP Scope

The MVP must include:

- PDF upload
- Collection management
- Asynchronous document ingestion
- Layout-aware text extraction
- Page and section metadata preservation
- Fixed-token and section-aware chunking
- Dense embeddings
- BM25 sparse retrieval
- Hybrid retrieval using Reciprocal Rank Fusion
- Cross-encoder reranking
- Streaming grounded answers
- Page-level citations
- PDF evidence viewer
- Retrieval debugger
- Paper comparison table
- Evaluation dataset and evaluation runner
- Docker Compose development environment
- Automated tests
- GitHub Actions CI

### Explicitly out of scope for the MVP

Do not implement these until all MVP acceptance criteria pass:

- Autonomous agents
- Graph RAG
- Knowledge-graph extraction
- Contradiction detection
- Multimodal figure understanding
- Kubernetes
- Terraform
- Multi-tenant billing
- Complex role-based access control

---

## 5. Technology Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui or an equivalent accessible component library
- PDF.js for PDF viewing
- Apache ECharts, Plotly, or Recharts for charts
- Server-Sent Events for streamed answers and job progress

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic
- PostgreSQL
- pgvector
- Redis
- Celery
- MinIO for local S3-compatible storage

### Retrieval and ML

- PyMuPDF for PDF parsing
- Sentence Transformers for local embeddings
- BM25 for sparse retrieval
- Cross-encoder reranker
- NumPy and scikit-learn for evaluation
- Optional hosted LLM provider behind a provider interface
- MLflow for experiment and evaluation tracking

### Engineering

- Docker
- Docker Compose
- pytest
- Ruff
- mypy
- Playwright for critical frontend flows
- GitHub Actions

---

## 6. High-Level Architecture

```text
Browser
  |
  v
Next.js frontend
  |
  v
FastAPI application
  |------------------------|
  |                        |
  v                        v
PostgreSQL + pgvector     Redis
  |                        |
  v                        v
Metadata and vectors     Celery job queue
                           |
                           v
                     Ingestion workers
                           |
                           v
                    MinIO object storage
```

### Query pipeline

```text
User query
  |
  v
Query normalization
  |
  +--> Dense retrieval
  |
  +--> BM25 retrieval
  |
  v
Reciprocal Rank Fusion
  |
  v
Cross-encoder reranking
  |
  v
Context construction
  |
  v
LLM answer generation
  |
  v
Citation validation
  |
  v
Answer + evidence + diagnostics
```

---

## 7. Core Domain Model

### Collection

```text
id
name
description
created_at
updated_at
```

### Document

```text
id
collection_id
title
authors
publication_year
source_filename
storage_key
checksum
status
page_count
error_message
created_at
updated_at
```

Valid document statuses:

```text
uploaded
processing
ready
failed
```

### Chunk

```text
id
document_id
page_number
section_title
chunk_index
content
token_count
content_type
embedding
metadata_json
created_at
```

### QueryRun

```text
id
collection_id
query
retrieval_mode
answer
latency_ms
input_tokens
output_tokens
estimated_cost
created_at
```

### RetrievedChunk

```text
id
query_run_id
chunk_id
dense_score
bm25_score
rrf_score
reranker_score
final_rank
used_in_context
```

### Citation

```text
id
query_run_id
chunk_id
claim_text
citation_index
validation_status
```

---

## 8. Required Backend API

### Collections

```text
POST   /api/v1/collections
GET    /api/v1/collections
GET    /api/v1/collections/{collection_id}
DELETE /api/v1/collections/{collection_id}
```

### Documents

```text
POST   /api/v1/collections/{collection_id}/documents
GET    /api/v1/collections/{collection_id}/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/status
GET    /api/v1/documents/{document_id}/file
DELETE /api/v1/documents/{document_id}
```

### Search and questions

```text
POST /api/v1/collections/{collection_id}/search
POST /api/v1/collections/{collection_id}/ask
GET  /api/v1/query-runs/{query_run_id}
```

The `/ask` endpoint must support streamed events:

```text
retrieval_started
retrieval_completed
generation_token
citation_completed
run_completed
error
```

### Comparison

```text
POST /api/v1/collections/{collection_id}/compare
```

### Evaluation

```text
POST /api/v1/evaluations/run
GET  /api/v1/evaluations
GET  /api/v1/evaluations/{evaluation_id}
```

---

## 9. Document Ingestion Requirements

The ingestion pipeline must:

1. Validate file type and size.
2. Calculate a checksum and reject duplicate files within the same collection.
3. Save the original PDF to object storage.
4. Extract text page by page.
5. Preserve page numbers and section headings.
6. Normalize whitespace without destroying paragraph boundaries.
7. Generate chunks using the configured strategy.
8. Generate embeddings in batches.
9. Store chunks and embeddings transactionally.
10. Mark the document as ready only after all required stages succeed.
11. Save a useful error message when processing fails.

### Required chunking strategies

#### Fixed-token chunking

Configurable values:

```text
chunk_size
chunk_overlap
```

#### Section-aware chunking

Keep section context and paragraph boundaries where possible. Oversized sections may be divided into smaller chunks.

Every chunk must retain:

- document ID
- page number
- section title
- chunk index
- token count
- chunking strategy

---

## 10. Retrieval Requirements

Implement retrieval without hiding the main logic behind a framework.

### Dense retrieval

- Store embeddings with pgvector.
- Support cosine similarity.
- Allow configurable `top_k`.

### Sparse retrieval

- Use BM25.
- Preserve the sparse score for debugging.

### Hybrid retrieval

Use Reciprocal Rank Fusion:

```text
RRF(d) = sum(1 / (k + rank_i(d)))
```

The constant `k` must be configurable.

### Reranking

- Retrieve a larger candidate pool first.
- Rerank candidates using a cross-encoder.
- Preserve all intermediate scores.
- Make reranking optional through configuration.

### Metadata filtering

At minimum support:

- document IDs
- publication year
- section title
- page range

---

## 11. Answer Generation and Citations

The generation layer must:

- Use only retrieved context.
- Clearly state when evidence is insufficient.
- Attach citation markers to factual claims.
- Return structured citation metadata.
- Never invent page numbers or document titles.
- Keep quoted text short.
- Prefer paraphrased answers.

Every citation must map to a real stored chunk.

The backend must validate:

1. The cited chunk exists.
2. The chunk belongs to the selected collection.
3. The page number matches stored metadata.
4. The cited evidence was included in the generation context.

Unsupported citations must not be displayed as valid.

---

## 12. Frontend Requirements

### Main workspace

Use a three-panel desktop layout:

```text
Documents | Answer and conversation | Evidence and retrieval details
```

On smaller screens, panels may become tabs or drawers.

### Required pages

```text
/
 /collections
 /collections/[id]
 /collections/[id]/ask
 /collections/[id]/documents
 /collections/[id]/compare
 /collections/[id]/retrieval-lab
 /evaluations
```

### Required visual components

- Drag-and-drop PDF upload
- Ingestion progress indicator
- Streaming answer display
- Clickable citation badges
- PDF viewer opening at the cited page
- Highlighted source passage
- Retrieved-chunk cards
- Score breakdown for dense, BM25, RRF, and reranker scores
- Retrieval pipeline visualization
- Paper-comparison table
- Evaluation charts
- Latency and token-usage indicators

### Design direction

- Clean technical interface
- Strong spacing and typography
- Dark and light mode
- Accessible contrast
- Minimal decorative animation
- No excessive gradients or badges
- Prioritize evidence and diagnostics over visual clutter

---

## 13. Evaluation Framework

Create a version-controlled evaluation dataset using JSONL.

Example:

```json
{
  "question": "What dataset was used to evaluate the proposed model?",
  "collection_id": "example-collection",
  "relevant_chunk_ids": ["chunk-1", "chunk-8"],
  "reference_answer": "The model was evaluated on ...",
  "answerable": true,
  "tags": ["single-document", "factual"]
}
```

### Required retrieval metrics

- Recall@k
- Precision@k
- Mean Reciprocal Rank
- nDCG
- Hit rate

### Required generation metrics

- Citation precision
- Citation recall
- Groundedness
- Answer relevance
- Unsupported-claim rate

### Required operational metrics

- Retrieval latency
- Reranking latency
- Generation latency
- End-to-end latency
- Input tokens
- Output tokens
- Estimated cost

Do not fabricate evaluation results. Only display metrics produced by actual runs.

---

## 14. Repository Structure

```text
evidencegraph/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── ingestion/
│   │   ├── chunking/
│   │   ├── embeddings/
│   │   ├── retrieval/
│   │   ├── reranking/
│   │   ├── generation/
│   │   ├── citations/
│   │   └── evaluation/
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml
├── workers/
├── evaluation_data/
├── sample_papers/
├── scripts/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── decisions/
│   └── implementation-plan.md
└── .github/
    └── workflows/
```

`AGENTS.md` and `CLAUDE.md` should contain the same project rules. Use one as the source and copy or link it to the other.

---

## 15. Development Rules for Coding Agents

When implementing a task:

1. Read this specification and the relevant existing code.
2. State the files expected to change.
3. Make the smallest coherent implementation.
4. Add or update tests in the same change.
5. Run formatting, linting, type checking, and relevant tests.
6. Report commands executed and their results.
7. Update documentation when behavior or architecture changes.
8. Do not silently change public API contracts.
9. Do not introduce a dependency unless it solves a clear requirement.
10. Do not leave placeholder code presented as complete.
11. Do not fabricate external service responses, benchmarks, or metrics.
12. Prefer explicit, testable Python over excessive framework abstraction.
13. Keep retrieval algorithms in project-owned modules.
14. Use structured logging.
15. Never commit secrets or real credentials.

When blocked, document:

- What is blocked
- Why it is blocked
- What was attempted
- The smallest decision required to continue

---

## 16. Code Quality Requirements

### Python

- Type hints on public functions
- Pydantic models for API input and output
- Ruff formatting and linting
- mypy on core modules
- pytest for unit and integration tests
- Dependency injection for external services
- No broad `except Exception` without logging and re-raising or returning a controlled error

### TypeScript

- Strict TypeScript mode
- No unexplained `any`
- Reusable typed API client
- Loading, empty, and error states for all data-driven components
- Accessible buttons, forms, dialogs, and navigation
- Playwright tests for critical user flows

---

## 17. Security and Reliability

- Validate uploaded MIME type and file signature.
- Enforce configurable upload-size limits.
- Sanitize filenames.
- Store files under generated keys, not user-provided paths.
- Apply request timeouts.
- Add rate limiting to query endpoints.
- Do not render untrusted HTML from documents.
- Keep provider API keys on the server.
- Add retry behavior only for idempotent operations.
- Make ingestion jobs safe to retry.
- Delete associated chunks and stored files when a document is deleted.
- Log failures with correlation IDs.

Prompt-injection defense for document content:

- Treat retrieved documents as untrusted data.
- Instruct the generation model not to follow instructions found inside documents.
- Never expose system prompts or secrets.
- Do not allow retrieved text to modify tool permissions or application configuration.

---

## 18. Local Development Commands

The exact commands may change, but the repository must provide equivalents for:

```bash
docker compose up -d postgres redis minio
docker compose up --build
```

Backend:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

Provide a root-level setup command through either a `Makefile`, `justfile`, or task runner.

---

## 19. Environment Variables

Document all variables in `.env.example`.

Minimum expected variables:

```text
DATABASE_URL
REDIS_URL
S3_ENDPOINT_URL
S3_ACCESS_KEY
S3_SECRET_KEY
S3_BUCKET
EMBEDDING_MODEL_NAME
RERANKER_MODEL_NAME
LLM_PROVIDER
LLM_MODEL
LLM_API_KEY
MAX_UPLOAD_MB
DEFAULT_DENSE_TOP_K
DEFAULT_SPARSE_TOP_K
DEFAULT_RERANK_TOP_K
RRF_K
```

The application must start without a hosted LLM key in a limited local mode. In this mode, ingestion and retrieval should work, while answer generation should display a clear configuration message.

---

## 20. Implementation Phases

### Phase 0 — Repository foundation

- Initialize monorepo
- Add Docker Compose
- Configure backend and frontend
- Add linting, formatting, type checking, and CI
- Add health endpoints

### Phase 1 — Collections and document storage

- Collection CRUD
- PDF upload
- MinIO storage
- Document metadata
- Ingestion status

### Phase 2 — Parsing and chunking

- Page-aware extraction
- Fixed-token chunking
- Section-aware chunking
- Unit tests with sample PDFs

### Phase 3 — Embeddings and dense retrieval

- Embedding provider interface
- pgvector migration
- Batch embedding generation
- Dense search endpoint

### Phase 4 — Sparse, hybrid, and reranked retrieval

- BM25 index
- RRF fusion
- Cross-encoder reranking
- Retrieval diagnostics

### Phase 5 — Grounded answers and citations

- LLM provider interface
- Streaming generation
- Citation mapping
- Citation validation
- Insufficient-evidence handling

### Phase 6 — Frontend research workspace

- Upload experience
- Chat workspace
- Evidence panel
- PDF citation navigation
- Retrieval pipeline visualization

### Phase 7 — Comparison and evaluation

- Paper comparison
- JSONL evaluation dataset
- Evaluation runner
- Metrics dashboard
- MLflow logging

### Phase 8 — Hardening and deployment readiness

- Rate limits
- Structured logging
- Error handling
- Integration tests
- End-to-end tests
- Demo data
- Documentation
- Recorded demo workflow

Complete phases in order. Do not begin advanced features while earlier acceptance criteria are failing.

---

## 21. MVP Acceptance Criteria

The MVP is complete only when all of the following are true:

- A user can create a collection.
- A user can upload at least five PDFs.
- Upload processing occurs asynchronously.
- Processing status is visible in the UI.
- Extracted chunks preserve page metadata.
- Dense retrieval returns relevant chunks.
- BM25 retrieval returns relevant chunks.
- Hybrid retrieval can be selected.
- Reranking can be enabled or disabled.
- Intermediate retrieval scores are visible.
- A user can ask a multi-document question.
- The answer contains clickable citations.
- Every citation opens a real PDF page.
- Every displayed citation maps to context actually used for generation.
- The system says when evidence is insufficient.
- The comparison page generates a source-linked table.
- The evaluation runner produces real retrieval metrics.
- Backend unit and integration tests pass.
- Critical frontend flow tests pass.
- CI passes from a clean checkout.
- The project can be started with documented commands.
- No proprietary or confidential data is included.

---

## 22. First Implementation Task

Start with Phase 0 only.

Deliver:

1. Repository structure.
2. Docker Compose services for PostgreSQL with pgvector, Redis, and MinIO.
3. FastAPI application with `/health/live` and `/health/ready`.
4. Next.js application with a basic landing page.
5. Backend and frontend linting and type checking.
6. GitHub Actions workflow.
7. `.env.example`.
8. Root README with exact startup commands.
9. Tests for the backend health endpoints.
10. A short architecture decision record explaining the monorepo choice.

Do not implement RAG features in the first task.

Before editing, inspect the current repository. After editing, run all available checks and report any failures honestly.
