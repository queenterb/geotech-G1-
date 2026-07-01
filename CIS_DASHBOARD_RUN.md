# Run CIS Dashboard (local development)

This document explains how to run the newly scaffolded CIS dashboard stack locally using Docker Compose.

Prerequisites
- Docker & Docker Compose installed
- Repository cloned and current working directory set to repository root

Quick start

1. Build and start services:

```bash
docker-compose up --build -d
```

2. Initialize the backend database (exec into container and run init script):

```bash
docker exec -it cis-dashboard-backend /bin/sh
python -m app.db.init_db
exit
```

3. Open the frontend via Nginx reverse proxy: http://localhost:8080

Direct CIS → Backend forwarding

The CIS detector can post alerts directly to the dashboard API. Configure either `cis/config.json` with `siem_http_endpoint` and an optional `siem_bearer_token`/`siem_api_key`, or set the following environment variables when running CIS:

- `CIS_SIEM_HTTP_ENDPOINT` — URL of the backend alerts endpoint (example: `http://backend:8000/api/alerts`)
- `CIS_SIEM_BEARER_TOKEN` or `CIS_SIEM_API_KEY` — optional authentication token sent as `Authorization: Bearer <token>` or `X-API-Key: <token>`

Example (Docker Compose env vars are provided in `docker-compose.yml` for local development):

```bash
docker-compose up --build -d
```

Add CI secret for smoke tests

The GitHub Actions workflow runs a docker-compose smoke test and expects a `SIEM_SHARED_SECRET` secret available to the `build-and-smoke` job. Add it in your repository settings:

1. Go to GitHub → Settings → Secrets and variables → Actions → New repository secret.
2. Name: `SIEM_SHARED_SECRET`.
3. Value: set to a secure token (for local dev you can use `dev_cis_token_change_me`).

The CI job reads the secret into the environment for the smoke test.

Troubleshooting

- Check container logs:

```bash
docker-compose logs -f backend
```

- Ensure the `cis` detector is configured to post alerts (see `cis/config.json` and `cis/config.example.json` for available `siem_*` options).
