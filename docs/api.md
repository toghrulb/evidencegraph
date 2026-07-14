# API

Phase 0 implements only operational health endpoints. No collection, document, search, question, comparison, or evaluation endpoint is available yet.

## `GET /health/live`

Reports whether the FastAPI process can serve a request.

Successful response (`200 OK`):

```json
{
  "status": "ok"
}
```

## `GET /health/ready`

Reports whether FastAPI lifecycle startup has completed. During startup or shutdown it returns `503 Service Unavailable`; while ready it returns `200 OK`.

Ready response:

```json
{
  "status": "ready"
}
```

Not-ready response:

```json
{
  "status": "not_ready"
}
```

Phase 0 readiness is an application-lifecycle signal, not a dependency connectivity check. Dependency-specific readiness will be introduced when those dependencies are used by an implemented feature.

Interactive OpenAPI documentation is available at `/docs` while the backend is running.
