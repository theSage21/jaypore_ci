# 00 — Golang Lint, Build & Test

A minimal Jaypore CI example that lints, builds, tests, and optionally
publishes a Go HTTP server.

## What's in the box

| File | Purpose |
|---|---|
| `main.go` | Tiny HTTP server with a `/health` endpoint (`{"status":"ok"}`) |
| `main_test.go` | Tests for status code, content-type, and response body |
| `.jci/run.sh` | CI pipeline script executed by Jaypore CI |

## Pipeline steps

1. **Module init** — runs `go mod init` if no `go.mod` is present.
2. **Lint** — `go vet ./...` (report saved to `$JCI_OUTPUT_DIR/vet-report.txt`).
3. **Format check** — `gofmt -l .` fails the build if any file is unformatted.
4. **Build** — compiles the binary to `$JCI_OUTPUT_DIR/server`.
5. **Test** — `go test -v -cover ./...` (results saved to `$JCI_OUTPUT_DIR/test-results.txt`).
6. **Publish** — copies the binary to `$PUBLISH_DIR` when the variable is set;
   skips gracefully otherwise.

## Environment variables

| Variable | Provided by | Description |
|---|---|---|
| `JCI_COMMIT` | Jaypore CI | Git commit SHA being built |
| `JCI_REPO_ROOT` | Jaypore CI | Absolute path to the repository root |
| `JCI_OUTPUT_DIR` | Jaypore CI | Directory for build artefacts (also the initial cwd) |
| `PUBLISH_DIR` | User (optional) | If set, the binary is copied here after a successful build |

## Running locally

```bash
export JCI_COMMIT=$(git rev-parse HEAD)
export JCI_REPO_ROOT=$(pwd)
export JCI_OUTPUT_DIR=$(mktemp -d)
bash 00-golang-lint-build-test/.jci/run.sh
```
