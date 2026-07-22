# API

Phase 2 retains every Phase 1 collection/document route and adds processing metadata plus a read-only chunk diagnostic. Search, questions, embeddings, and retrieval remain unavailable.

## Collections

```text
POST   /api/v1/collections
GET    /api/v1/collections
GET    /api/v1/collections/{collection_id}
DELETE /api/v1/collections/{collection_id}
```

Deleting a collection removes original PDFs, parsed intermediate objects, document metadata, and cascaded chunks.

## Upload a document

`POST /api/v1/collections/{collection_id}/documents` accepts `multipart/form-data`:

- `file`: required PDF
- `title`: optional; defaults to the sanitized filename stem
- `authors`: optional repeated field
- `publication_year`: optional integer
- `chunking_strategy`: optional `fixed_token` or `section_aware`; defaults to configuration

Upload validation streams the file and checks MIME type, `.pdf` filename, byte limit, and `%PDF-` signature. SHA-256 prevents duplicate bytes within one collection. The worker then rechecks the stored object, signature, size, encryption, readability, and page limit.

Document detail responses preserve the Phase 1 fields and add:

```json
{
  "status": "processing",
  "processing_stage": "parsing",
  "page_count": null,
  "chunk_count": 0,
  "chunking_strategy": "section_aware",
  "processing_started_at": "<timestamp-or-null>",
  "processing_completed_at": null,
  "error_message": null,
  "error_code": null
}
```

`status` remains one of `uploaded`, `processing`, `ready`, or `failed`. `processing_stage` is one of `uploaded`, `processing`, `parsing`, `chunking`, `ready`, or `failed`. A controlled failure returns safe `error_message` text and a stable `error_code`.

## Other document routes

```text
GET    /api/v1/collections/{collection_id}/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/status
GET    /api/v1/documents/{document_id}/file
GET    /api/v1/documents/{document_id}/chunks?offset=0&limit=50
DELETE /api/v1/documents/{document_id}
```

The status route exposes lifecycle, page/chunk counts, strategy, timestamps, and controlled errors. The file route streams the unchanged original PDF.

The chunk route is diagnostic and offset-paginated (`offset >= 0`, `1 <= limit <= 100`). It returns `items`, `total`, `offset`, and `limit`. Items are in `chunk_index` source order and contain page range, optional section title, content, token/character counts, content type, strategy, version, and safe provenance metadata. Internal MinIO keys are never returned. A missing document returns `404`.

Deleting a document removes its original and parsed objects; the database foreign key cascades chunk deletion.

Health routes remain `GET /health/live` and `GET /health/ready`. Interactive OpenAPI documentation is available at `/docs`.
