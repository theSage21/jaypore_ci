# 13 — Jekyll + Netlify

Build a Jekyll static site and (optionally) deploy it to Netlify.

## What this example does

1. Checks that Jekyll is installed; installs it via `gem` if missing.
2. Runs `jekyll build` to generate the static site into `$JCI_OUTPUT_DIR/_site`.
3. Verifies the build succeeded and lists output files.
4. If `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` are set, zips the output and
   deploys it to Netlify via the Netlify API. Otherwise it skips the deploy
   gracefully.
5. Writes a build log to `$JCI_OUTPUT_DIR/build.log`.

## Files

| Path | Purpose |
|------|---------|
| `.jci/run.sh` | CI entry point |
| `site/index.md` | Sample Jekyll page |
| `site/_config.yml` | Minimal Jekyll configuration |
| `site/_layouts/default.html` | Bare-bones HTML layout |

## Environment variables

| Variable | Description |
|----------|-------------|
| `JCI_COMMIT` | Git commit SHA being built |
| `JCI_REPO_ROOT` | Root of the repository checkout |
| `JCI_OUTPUT_DIR` | Directory for build artifacts (also the initial cwd) |
| `NETLIFY_AUTH_TOKEN` | *(optional)* Netlify personal access token |
| `NETLIFY_SITE_ID` | *(optional)* Target Netlify site ID |

## Running locally

```bash
export JCI_COMMIT=$(git rev-parse HEAD)
export JCI_REPO_ROOT=$(pwd)
export JCI_OUTPUT_DIR=$(mktemp -d)

bash 13-jekyll-netlify/.jci/run.sh
```

To deploy, also set `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` before running.
