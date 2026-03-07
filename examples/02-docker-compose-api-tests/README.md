# 02 — Docker Compose API Tests

This Jaypore CI example shows how to bring up a multi-service stack with
**Docker Compose** and run API tests against it.

## What’s in the stack

| Service    | Image                | Purpose                       |
|------------|----------------------|-------------------------------|
| `postgres` | `postgres:16-alpine` | Primary database              |
| `redis`    | `redis:7-alpine`     | Cache / message broker        |
| `web`      | Built from repo      | Django app serving the API    |

All three services have Docker health checks so the CI script can wait
until everything is ready before running tests.

## Files

```
02-docker-compose-api-tests/
├── .jci/
│   └── run.sh            # Jaypore CI entry point
├── docker-compose.yml    # Service definitions
├── Dockerfile            # Django app image
├── test_api.sh           # Curl-based API test suite
└── README.md             # This file
```

## How it works

1. **`.jci/run.sh`** is executed by Jaypore CI.  
   It receives `JCI_COMMIT`, `JCI_REPO_ROOT`, and `JCI_OUTPUT_DIR` as
   environment variables.

2. The script runs `docker compose up -d --build` to start postgres,
   redis, and the Django web service.

3. It polls the Docker health checks until all three services report
   healthy (up to 120 s).

4. **`test_api.sh`** fires `curl` requests at the Django app:
   - `GET /health/` — expects `{"status": "ok"}`
   - `GET /items/` — expects a JSON list of items
   - `GET /nonexistent/` — expects a 404

5. Results are saved into `$JCI_OUTPUT_DIR` so they become CI artifacts:
   - `api-test-results.txt` — pass/fail summary
   - `test-output.log` — full test console output
   - `compose-logs.log` — container logs for debugging
   - `compose-up.log` — docker compose build/start output

6. `docker compose down` tears everything down (via a `trap` so it runs
   even on failure).

## Running locally

```bash
export JCI_COMMIT=$(git rev-parse HEAD)
export JCI_REPO_ROOT=$(git rev-parse --show-toplevel)
export JCI_OUTPUT_DIR=$(mktemp -d)

bash 02-docker-compose-api-tests/.jci/run.sh

ls "$JCI_OUTPUT_DIR"   # see the artifacts
```
