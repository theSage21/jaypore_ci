# Example 10 — Build & Publish Docker Images

This Jaypore CI example builds a production Docker image for the Django
project, runs the test suite inside the container, and optionally pushes the
image to a Docker registry.

| Step | What it does |
|------|--------------|
| 1 | **Build** the Docker image, tagged with the commit SHA and `latest`. |
| 2 | **Test** — run `manage.py test` inside the freshly built container. |
| 3 | **Inspect** — save `docker inspect` output and image size info. |
| 4 | **Push** — if `DOCKER_REGISTRY` is set, log in and push both tags. |

## Dockerfile

The included `Dockerfile` creates a slim production image:

- **Base** — `python:3.12-slim`
- **Dependencies** — installs `requirements.txt` plus `gunicorn`
- **App code** — copies `manage.py`, `mysite/`, `core/`, and `setup.cfg`
- **Entrypoint** — runs Gunicorn on port 8000 with 2 workers

## Artifacts produced

| File | Description |
|------|-------------|
| `docker-build.log` | Full `docker build` output. |
| `docker-test.log` | Test suite output from inside the container. |
| `image-inspect.json` | `docker inspect` metadata for the built image. |
| `image-info.txt` | Image repository, tag, ID, and size. |
| `docker-push.log` | Registry push output (only when pushing). |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_REGISTRY` | No | Registry hostname (e.g. `registry.example.com`). If unset, the image is built and tested locally but not pushed. |
| `DOCKER_USERNAME` | No | Username for `docker login`. |
| `DOCKER_PASSWORD` | No | Password / token for `docker login`. |

## Project layout assumed

```
your-repo/
├── manage.py
├── requirements.txt
├── setup.cfg
├── mysite/
│   └── settings.py
├── core/
└── 10-build-publish-docker/
    ├── Dockerfile
    └── .jci/
        └── run.sh       # ← this script
```

## How to use

1. Copy the `.jci/` directory and `Dockerfile` into your repository:

   ```bash
   cp -r 10-build-publish-docker/.jci /path/to/your-repo/.jci
   cp 10-build-publish-docker/Dockerfile /path/to/your-repo/Dockerfile
   ```

2. Make sure Docker is available on the CI runner.

3. Run Jaypore CI:

   ```bash
   git jci run
   ```

   To also push to a registry, export the environment variables first:

   ```bash
   export DOCKER_REGISTRY=registry.example.com
   export DOCKER_USERNAME=deploy-bot
   export DOCKER_PASSWORD=secret-token
   git jci run
   ```

## Customisation

- **Image name** — change `IMAGE_NAME` in `run.sh` to match your project.
- **Build context** — adjust the `-f` flag and build context path if your
  `Dockerfile` lives elsewhere.
- **Multi-platform builds** — replace `docker build` with `docker buildx build
  --platform linux/amd64,linux/arm64` for multi-arch images.
- **Gunicorn workers** — edit the `CMD` in `Dockerfile` or set the
  `WEB_CONCURRENCY` environment variable at runtime.
