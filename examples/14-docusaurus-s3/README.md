# 14 — Build Docusaurus & Publish to S3

This example shows how to build a documentation site and deploy the static
output to an AWS S3 bucket using Jaypore CI.

## How it works

1. **Build** — The CI script checks for a real Docusaurus project
   (`package.json` containing `docusaurus`). If found it runs `npm run build`;
   otherwise it falls back to a lightweight `build.sh` that converts Markdown
   to HTML with pandoc (or plain sed when pandoc is unavailable).

2. **Artifact collection** — The generated HTML is copied to
   `$JCI_OUTPUT_DIR/build/` so it is available as a CI artifact.

3. **S3 deploy** — If AWS credentials and an S3 bucket are configured the
   output is synced to S3 with `aws s3 sync`. If the variables are missing
   the deploy step is skipped gracefully.

## Using a real Docusaurus project

For a production setup, replace the simple `docs/` + `build.sh` scaffold with
a full Docusaurus project:

```bash
npx create-docusaurus@latest my-docs classic
```

Then place the generated project files in this directory. The CI script will
automatically detect `package.json` and run `npm run build` instead of the
fallback.

## Configuring S3 credentials

Set these environment variables (e.g. in your Jaypore CI secrets):

| Variable                | Required | Description                          |
|-------------------------|----------|--------------------------------------|
| `AWS_ACCESS_KEY_ID`     | Yes      | AWS access key                       |
| `AWS_SECRET_ACCESS_KEY` | Yes      | AWS secret key                       |
| `S3_BUCKET`             | Yes      | Target bucket, e.g. `s3://my-docs`   |
| `AWS_REGION`            | No       | AWS region (default `us-east-1`)     |

Without these variables the pipeline still succeeds — it simply skips the
deploy step and prints a message.

## Files

```
14-docusaurus-s3/
├── .jci/
│   └── run.sh        # Jaypore CI entry point
├── docs/
│   └── index.md      # Sample documentation page
├── build.sh          # Lightweight Markdown → HTML builder
└── README.md         # This file
```
