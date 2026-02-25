# git-jci

A local-first CI system that stores results in git's custom refs.

## Installation

### From source

```bash
go build -o git-jci ./cmd/git-jci
sudo mv git-jci /usr/local/bin/
```

### From CI artifacts

If CI has run, you can download the pre-built static binary:

```bash
# One-liner: download and install from running JCI web server
curl -fsSL http://localhost:8000/jci/$(git rev-parse HEAD)/git-jci -o /tmp/git-jci && sudo install /tmp/git-jci /usr/local/bin/

# Or from a specific commit
curl -fsSL http://localhost:8000/jci/<commit>/git-jci -o /tmp/git-jci && sudo install /tmp/git-jci /usr/local/bin/
```

The binary is fully static (no dependencies) and works on any Linux system.

Once installed, git will automatically find it as a subcommand:

```bash
git jci run
```

## Setup

Create a `.jci/run.sh` script in your repository:

```bash
mkdir -p .jci
cat > .jci/run.sh << 'EOF'
#!/bin/bash
set -e

echo "Running tests..."
cd "$JCI_REPO_ROOT" && go test ./...

echo "Building..."
cd "$JCI_REPO_ROOT" && go build -o "$JCI_OUTPUT_DIR/binary" ./cmd/...

echo "Done!"
EOF
chmod +x .jci/run.sh
```

### Environment Variables

Your `run.sh` script has access to:

| Variable | Description |
|----------|-------------|
| `JCI_COMMIT` | Full commit hash |
| `JCI_REPO_ROOT` | Repository root path |
| `JCI_OUTPUT_DIR` | Output directory for artifacts |

The script runs with `cwd` set to `JCI_OUTPUT_DIR`. Any files created there become CI artifacts.

## Commands

### `git jci run`

Run CI for the current commit:

```bash
git commit -m "My changes"
git jci run
```

This will:
1. Execute `.jci/run.sh`
2. Capture stdout/stderr to `run.output.txt`
3. Store all output files (artifacts) in `refs/jci/<commit>`
4. Generate an `index.html` with results

### `git jci web [port]`

Start a web server to view CI results. Default port is 8000.

```bash
git jci web
git jci web 3000
```

### `git jci push [remote]`

Push CI results to a remote. Default remote is `origin`.

```bash
git jci push
git jci push upstream
```

### `git jci pull [remote]`

Fetch CI results from a remote.

```bash
git jci pull
```

### `git jci prune`

Remove CI results for commits that no longer exist in the repository.

```bash
git jci prune
```

## How it works

CI results are stored as git tree objects under the `refs/jci/` namespace.
This keeps them separate from your regular branches and tags, but still
part of the git repository.

- Results are not checked out to the working directory
- They can be pushed/pulled like any other refs
- They are garbage collected when the original commit is gone (via `prune`)
- Each commit's CI output is stored as a separate commit object
