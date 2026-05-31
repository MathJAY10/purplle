# Production Validation Checklist

## Verified

- `python -m compileall app tests` passes.
- `python -m pytest -q` passes.
- Docker Compose includes API, worker, Redis, and PostgreSQL.
- Healthchecks are defined for API, Redis, and PostgreSQL.
- Restart policies are enabled.
- The Redis event pipeline is operational.
- Metrics and health endpoints are operational.
- Worker persistence is operational.

## Manual Docker Verification

Run the following on a fresh environment:

```bash
cp .env.example .env
docker compose up --build
```

Then verify:

- `GET /health`
- `GET /api/v1/stores/{id}/metrics`
- `POST /api/v1/events/ingest`
