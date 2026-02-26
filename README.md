# Jaypore CI

> Minimal, Offline, Local CI system.

## Installation

```bash
go build -o git-jci ./cmd/git-jci
sudo mv git-jci /usr/local/bin/
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

## Minimal workflow

```bash
cd repo-dir && git status   # enter the repository and check the working tree
git add -A                  # stage every modified, deleted, or new file
git commit -m "..."         # record the staged changes in a new commit
git jci run                 # execute .jci/run.sh manually and capture artifacts for this commit. You could also use git hooks to run this automatically on commit.
git jci web                 # launch the local viewer to inspect the latest CI results
git jci push                # push the commit's CI artifacts to the default remote
git jci pull                # fetch updated CI artifacts from the remote
git jci prune               # delete CI refs for commits that no longer exist locally
git jci cron ls             # list cron jobs that are there in .jci/crontab
git jci cron sync           # sync local machine's crontab with the current contents of .jci/crontab 
```

## How it works

CI results are stored as git tree objects under the `refs/jci/` namespace.
This keeps them separate from your regular branches and tags, but still
part of the git repository.

- Results are not checked out to the working directory
- They can be pushed/pulled like any other refs
- They are garbage collected when the original commit is gone (via `prune`)
- Each commit's CI output is stored as a separate commit object

## Use cases

- [ ] Automate unit, integration, and end-to-end test suites on every commit
- [ ] Run linting and static analysis to enforce coding standards
- [ ] Produce code coverage reports and surface regressions
- [ ] Build, package, and archive release artifacts across target platforms
- [ ] Perform dependency and source code security scans (SCA/SAST)
- [ ] Execute performance and regression benchmarks with historical comparisons
- [ ] Generate documentation sites and preview environments for review
- [ ] Validate infrastructure-as-code changes and deployment pipelines via dry runs
- [ ] Schedule recurring workflows (cron-style) for maintenance tasks
- [ ] Notify developers and stakeholders when CI statuses change or regress


## Platform features

- [x] Complex pipeline definitions
- [x] Artifacts
- [x] Debug CI locally
- [ ] Build farms / remote runners on cloud
- [ ] Community / marketplace runners contributed by external teams
- [ ] Shared runner pools across repositories and organizations
- [ ] Deploy keys / scoped access tokens so runners can securely pull & push repos
- [ ] Built-in secrets management with masking, rotation, and per-environment scoping
- [ ] Merge request / PR status reporting, required-check gating, and review UIs
- [ ] Line-by-line coverage overlays and annotations directly on PR/MR diffs
- [ ] Deployment environments with history, approvals, and promotion policies
- [ ] First-class integration with observability / error tracking tools (e.g., Sentry)
- [ ] Ecosystem of reusable actions/tasks with versioned catalogs and templates
