# Documentation

> Jaypore CI: Minimal, Offline, Local CI system.

---

- [Install](#install)
- [Config](#config)
- [Environment Vars](#environment-vars)
- [Example workflow](#example-workflow)
- [How it works](#how-it-works)
- [FAQ / Needs / Wants / Todos](#faq-needs-wants-todos)
- [Examples](#examples)
    - [Lint, Build, Test, Publish a golang project](#lint-build-test-publish-a-golang-project)
    - [Pylint, Pytest, Coverage report](#pylint-pytest-coverage-report)
    - [Build Jekyll and publish to netlify](#build-jekyll-and-publish-to-netlify)
    - [Build Docusaurus and publish to S3 bucket](#build-docusaurus-and-publish-to-s3-bucket)
    - [Run a docker compose of redis, postgres, django, and run API tests against it.](#run-a-docker-compose-of-redis-postgres-django-and-run-api-tests-against-it)
    - [Schedule a midnight build and push status to telegram](#schedule-a-midnight-build-and-push-status-to-telegram)
    - [Run trufflehog scan on repo every hour](#run-trufflehog-scan-on-repo-every-hour)
    - [Run lint --fix on pre-commit for python, go, JS in the same repo](#run-lint-fix-on-pre-commit-for-python-go-js-in-the-same-repo)
    - [Create sub-pipelines for python / js / go and run when changes are there in any folder](#create-sub-pipelines-for-python-js-go-and-run-when-changes-are-there-in-any-folder)
    - [Set and use Secrets to publish messages to telegram](#set-and-use-secrets-to-publish-messages-to-telegram)
    - [Send mail on scheduled pipe failures](#send-mail-on-scheduled-pipe-failures)
    - [Midnight auto-update dependencies and ensure tests are passing after update](#midnight-auto-update-dependencies-and-ensure-tests-are-passing-after-update)
    - [Build and publish docker images](#build-and-publish-docker-images)
    - [Run pipelines on this repo, when changes happen in upstream projects](#run-pipelines-on-this-repo-when-changes-happen-in-upstream-projects)
    - [Run pipelines on another repo, when changes affect downstream projects](#run-pipelines-on-another-repo-when-changes-affect-downstream-projects)

---

## Install

```bash
# Download an appropriate binary from www.jayporeci.in
# After that move it to some location on your PATH
sudo mv git-jci /usr/local/bin/
```

The binary is fully static (no dependencies) and works on most systems. If you are having issues, please contact us.
Once installed, git will automatically find it as a subcommand and you can start using it via `git jci run`

## Config

Create a `.jci` folder in your repository. You can place a `run.sh` file and a `crontab` file in it.

> Make sure that run.sh is executable!

```
.jci/
├── crontab
└── run.sh
```

You can put anything in `run.sh`. Call a python program / run docker commands / replace it with a binary from a rust project that does something else entirely!

`crontab` is used to schedule things. You can run things like midnight tests / builds, SLA checks, repo auto-commits, repo time trackers etc.


## Environment Vars

Your `run.sh` script has access to:

| Variable | Description |
|----------|-------------|
| `JCI_COMMIT` | Full commit hash |
| `JCI_REPO_ROOT` | Repository root path |
| `JCI_OUTPUT_DIR` | Output directory for artifacts |

The script runs with `cwd` set to `JCI_OUTPUT_DIR`. Any files created there become CI artifacts.

## Example workflow

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

## FAQ / Needs / Wants / Todos

- [x] Complex pipeline definitions
    - `run.sh` can be an executable. Do whatever you like!
- [x] Artifacts
    - Anything in `JCI_OUTPUT_DIR` is an artifact!
- [x] Debug CI locally
    - Just execute `run.sh` locally.
- [x] Automate unit, integration, and end-to-end test suites on every commit
    - Link [git hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) and run CI whenever you want.
    - For integration / end to end, I like to use a docker-compose that will compose up services / databases etc, and one container is a test driver like [locust](https://locust.io/).
- [x] Run linting and static analysis to enforce coding standards
    - Link [git hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) and run CI whenever you want.
- [x] Produce code coverage reports and surface regressions
    - Outputs are placed in `JCI_OUTPUT_DIR`. We can put HTML coverage reports here if needed and view via CI browser.
    - For regressions, the `run.sh` can commit examples created by things like
      [hypothesis](https://hypothesis.readthedocs.io/en/latest/) back to the
      repo. This ensures that next runs will use those examples and test for
      regresssions.
- [x] Build, package, and archive release artifacts across target platforms
    - I like building a docker image, building stuff inside that, then publishing.
    - Refer to the [scripts/](http://127.0.0.1:8000/releases/files.html) files for examples on how to build/render etc.
- [x] Perform dependency and source code security scans (SCA/SAST)
    - I like to run [Truffle Hog](https://github.com/trufflesecurity/trufflehog) to prevent accidental leaks.
- [x] Generate documentation sites and preview environments for review
    - This Jaypore CI site itself is generated and published via CI.
- [x] Schedule recurring workflows (cron-style) for maintenance tasks
    - I run a nightly build via cron to ensure that I catch any dependency failures / security breaks. See [.jci/crontab](.jci/crontab.html) for an example.
- [x] Notify developers and stakeholders when CI statuses change or regress
    - As part of our scripts, we can call telegram / slack / email APIs and inform devs of changes.
- [ ] Built-in secrets management with masking, rotation, and per-environment scoping
    - I currently use [Mozilla SOPS](https://github.com/getsops/sops) for secrets but this might change in the future.
- [ ] Build farms / remote runners on cloud
- [ ] Community / marketplace runners contributed by external teams
- [ ] Shared runner pools across repositories and organizations
- [ ] Deploy keys / scoped access tokens so runners can securely pull & push repos
- [ ] Merge request / PR status reporting, required-check gating, and review UIs
    - It would be great to have some integration into PRs so that we can know if our colleagues have run CI jobs or not.
- [ ] Line-by-line coverage overlays and annotations directly on PR/MR diffs
    - This might be hard since it will depend a LOT on which remote is being used. Gitlab uses a cobertura file but others might not.
- [ ] Deployment environments with history, approvals, and promotion policies
- [ ] First-class integration with observability / error tracking tools (e.g., Sentry)
- [ ] Ecosystem of reusable actions/tasks with versioned catalogs and templates
    - This is already there? Not sure if this is something we even need to solve?
- [ ] Validate infrastructure-as-code changes and deployment pipelines via dry runs


## Examples

### 00 — Golang Lint, Build & Test

```
00-golang-lint-build-test/
├── .jci/
│   └── run.sh
├── README.md
├── main.go
└── main_test.go
```

- [examples/00-golang-lint-build-test/.jci/run.sh](/releases/files/examples/00-golang-lint-build-test/.jci/run.sh)
- [examples/00-golang-lint-build-test/README.md](/releases/files/examples/00-golang-lint-build-test/README.md)
- [examples/00-golang-lint-build-test/main.go](/releases/files/examples/00-golang-lint-build-test/main.go)
- [examples/00-golang-lint-build-test/main_test.go](/releases/files/examples/00-golang-lint-build-test/main_test.go)

### Example 01 — Pylint + Pytest + Coverage

```
01-pylint-pytest-coverage/
├── .jci/
│   └── run.sh
└── README.md
```

- [examples/01-pylint-pytest-coverage/.jci/run.sh](/releases/files/examples/01-pylint-pytest-coverage/.jci/run.sh)
- [examples/01-pylint-pytest-coverage/README.md](/releases/files/examples/01-pylint-pytest-coverage/README.md)

### 02 — Docker Compose API Tests

```
02-docker-compose-api-tests/
├── .jci/
│   └── run.sh
├── Dockerfile
├── README.md
├── docker-compose.yml
└── test_api.sh
```

- [examples/02-docker-compose-api-tests/.jci/run.sh](/releases/files/examples/02-docker-compose-api-tests/.jci/run.sh)
- [examples/02-docker-compose-api-tests/Dockerfile](/releases/files/examples/02-docker-compose-api-tests/Dockerfile)
- [examples/02-docker-compose-api-tests/README.md](/releases/files/examples/02-docker-compose-api-tests/README.md)
- [examples/02-docker-compose-api-tests/docker-compose.yml](/releases/files/examples/02-docker-compose-api-tests/docker-compose.yml)
- [examples/02-docker-compose-api-tests/test_api.sh](/releases/files/examples/02-docker-compose-api-tests/test_api.sh)

### Midnight Build with Telegram Notifications

```
03-midnight-build-telegram/
├── .jci/
│   ├── crontab
│   └── run.sh
└── README.md
```

- [examples/03-midnight-build-telegram/.jci/crontab](/releases/files/examples/03-midnight-build-telegram/.jci/crontab)
- [examples/03-midnight-build-telegram/.jci/run.sh](/releases/files/examples/03-midnight-build-telegram/.jci/run.sh)
- [examples/03-midnight-build-telegram/README.md](/releases/files/examples/03-midnight-build-telegram/README.md)

### TruffleHog Secret Scan

```
04-trufflehog-scan/
├── .jci/
│   ├── crontab
│   └── run.sh
└── README.md
```

- [examples/04-trufflehog-scan/.jci/crontab](/releases/files/examples/04-trufflehog-scan/.jci/crontab)
- [examples/04-trufflehog-scan/.jci/run.sh](/releases/files/examples/04-trufflehog-scan/.jci/run.sh)
- [examples/04-trufflehog-scan/README.md](/releases/files/examples/04-trufflehog-scan/README.md)

### 05 — Lint & Fix on Pre-Commit

```
05-lint-fix-precommit/
├── .jci/
│   └── run.sh
├── README.md
└── install-hook.sh
```

- [examples/05-lint-fix-precommit/.jci/run.sh](/releases/files/examples/05-lint-fix-precommit/.jci/run.sh)
- [examples/05-lint-fix-precommit/README.md](/releases/files/examples/05-lint-fix-precommit/README.md)
- [examples/05-lint-fix-precommit/install-hook.sh](/releases/files/examples/05-lint-fix-precommit/install-hook.sh)

### 06 — Sub-pipelines

```
06-sub-pipelines/
├── .jci/
│   └── run.sh
├── README.md
├── go-app/
│   ├── go-app
│   ├── go.mod
│   ├── main.go
│   └── main_test.go
├── js-app/
│   ├── index.js
│   └── package.json
└── python-app/
    ├── app.py
    └── test_app.py
```

- [examples/06-sub-pipelines/.jci/run.sh](/releases/files/examples/06-sub-pipelines/.jci/run.sh)
- [examples/06-sub-pipelines/README.md](/releases/files/examples/06-sub-pipelines/README.md)
- [examples/06-sub-pipelines/go-app/go-app](/releases/files/examples/06-sub-pipelines/go-app/go-app)
- [examples/06-sub-pipelines/go-app/go.mod](/releases/files/examples/06-sub-pipelines/go-app/go.mod)
- [examples/06-sub-pipelines/go-app/main.go](/releases/files/examples/06-sub-pipelines/go-app/main.go)
- [examples/06-sub-pipelines/go-app/main_test.go](/releases/files/examples/06-sub-pipelines/go-app/main_test.go)
- [examples/06-sub-pipelines/js-app/index.js](/releases/files/examples/06-sub-pipelines/js-app/index.js)
- [examples/06-sub-pipelines/js-app/package.json](/releases/files/examples/06-sub-pipelines/js-app/package.json)
- [examples/06-sub-pipelines/python-app/app.py](/releases/files/examples/06-sub-pipelines/python-app/app.py)
- [examples/06-sub-pipelines/python-app/test_app.py](/releases/files/examples/06-sub-pipelines/python-app/test_app.py)

### Example 07 — Secrets with SOPS + Telegram

```
07-secrets-telegram/
├── .jci/
│   └── run.sh
├── README.md
└── secrets.example.json
```

- [examples/07-secrets-telegram/.jci/run.sh](/releases/files/examples/07-secrets-telegram/.jci/run.sh)
- [examples/07-secrets-telegram/README.md](/releases/files/examples/07-secrets-telegram/README.md)
- [examples/07-secrets-telegram/secrets.example.json](/releases/files/examples/07-secrets-telegram/secrets.example.json)

### 08 — Mail on failure

```
08-mail-on-failure/
├── .jci/
│   ├── crontab
│   └── run.sh
└── README.md
```

- [examples/08-mail-on-failure/.jci/crontab](/releases/files/examples/08-mail-on-failure/.jci/crontab)
- [examples/08-mail-on-failure/.jci/run.sh](/releases/files/examples/08-mail-on-failure/.jci/run.sh)
- [examples/08-mail-on-failure/README.md](/releases/files/examples/08-mail-on-failure/README.md)

### Auto-Update Dependencies

```
09-auto-update-deps/
├── .jci/
│   ├── crontab
│   └── run.sh
└── README.md
```

- [examples/09-auto-update-deps/.jci/crontab](/releases/files/examples/09-auto-update-deps/.jci/crontab)
- [examples/09-auto-update-deps/.jci/run.sh](/releases/files/examples/09-auto-update-deps/.jci/run.sh)
- [examples/09-auto-update-deps/README.md](/releases/files/examples/09-auto-update-deps/README.md)

### Example 10 — Build & Publish Docker Images

```
10-build-publish-docker/
├── .jci/
│   └── run.sh
├── Dockerfile
└── README.md
```

- [examples/10-build-publish-docker/.jci/run.sh](/releases/files/examples/10-build-publish-docker/.jci/run.sh)
- [examples/10-build-publish-docker/Dockerfile](/releases/files/examples/10-build-publish-docker/Dockerfile)
- [examples/10-build-publish-docker/README.md](/releases/files/examples/10-build-publish-docker/README.md)

### 11 — Upstream Trigger

```
11-upstream-trigger/
└── README.md
```

- [examples/11-upstream-trigger/README.md](/releases/files/examples/11-upstream-trigger/README.md)

### 12 — Downstream Trigger

```
12-downstream-trigger/
└── README.md
```

- [examples/12-downstream-trigger/README.md](/releases/files/examples/12-downstream-trigger/README.md)

### 13 — Jekyll + Netlify

```
13-jekyll-netlify/
├── .jci/
│   └── run.sh
├── README.md
└── site/
    ├── _config.yml
    ├── _layouts/
    │   └── default.html
    └── index.md
```

- [examples/13-jekyll-netlify/.jci/run.sh](/releases/files/examples/13-jekyll-netlify/.jci/run.sh)
- [examples/13-jekyll-netlify/README.md](/releases/files/examples/13-jekyll-netlify/README.md)
- [examples/13-jekyll-netlify/site/_config.yml](/releases/files/examples/13-jekyll-netlify/site/_config.yml)
- [examples/13-jekyll-netlify/site/_layouts/default.html](/releases/files/examples/13-jekyll-netlify/site/_layouts/default.html)
- [examples/13-jekyll-netlify/site/index.md](/releases/files/examples/13-jekyll-netlify/site/index.md)

### 14 — Build Docusaurus & Publish to S3

```
14-docusaurus-s3/
├── .jci/
│   └── run.sh
├── README.md
├── build.sh
└── docs/
    └── index.md
```

- [examples/14-docusaurus-s3/.jci/run.sh](/releases/files/examples/14-docusaurus-s3/.jci/run.sh)
- [examples/14-docusaurus-s3/README.md](/releases/files/examples/14-docusaurus-s3/README.md)
- [examples/14-docusaurus-s3/build.sh](/releases/files/examples/14-docusaurus-s3/build.sh)
- [examples/14-docusaurus-s3/docs/index.md](/releases/files/examples/14-docusaurus-s3/docs/index.md)
