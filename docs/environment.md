# Environment variables

`.env.example` contains safe local defaults. Copy it to `.env` and keep real credentials out of Git.

## Phase 2 processing

| Variable | Default | Purpose |
|---|---:|---|
| `MAX_UPLOAD_MB` | `50` | Maximum original PDF size during upload and worker reload |
| `MAX_PDF_PAGES` | `500` | Maximum readable PDF page count |
| `DEFAULT_CHUNKING_STRATEGY` | `section_aware` | Default `fixed_token` or `section_aware` strategy |
| `FIXED_CHUNK_SIZE` | `512` | Maximum tokens per chunk for both current strategies |
| `FIXED_CHUNK_OVERLAP` | `64` | Target token overlap inside a logical group |
| `MINIMUM_CHUNK_SIZE` | `64` | Preferred minimum chunk size and short-page merge threshold |
| `TOKENIZER_NAME` | `unicode_lexical_v1` | Versioned local tokenizer implementation |
| `PARSER_VERSION` | `pymupdf-v1` | Parser behavior version stored in intermediate/chunk metadata |
| `CHUNKING_CONFIG_VERSION` | `v1` | Chunk configuration version stored on every chunk |

Startup validation rejects non-positive bounds, overlap greater than or equal to chunk size, minimum size greater than chunk size, unknown strategies, and unknown tokenizers.

Infrastructure variables configure PostgreSQL, Redis, and MinIO. The ML/retrieval variables remain documented in `.env.example` for later phases but are not consumed by Phase 2.
