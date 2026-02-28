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

### Lint, Build, Test, Publish a golang project
### Pylint, Pytest, Coverage report
### Build Jekyll and publish to netlify
### Build Docusaurus and publish to S3 bucket
### Run a docker compose of redis, postgres, django, and run API tests against it.
### Schedule a midnight build and push status to telegram
### Run trufflehog scan on repo every hour
### Run lint --fix on pre-commit for python, go, JS in the same repo
### Create sub-pipelines for python / js / go and run when changes are there in any folder
### Set and use Secrets to publish messages to telegram
### Send mail on scheduled pipe failures
### Midnight auto-update dependencies and ensure tests are passing after update
### Build and publish docker images
### Run pipelines on this repo, when changes happen in upstream projects
### Run pipelines on another repo, when changes affect downstream projects
