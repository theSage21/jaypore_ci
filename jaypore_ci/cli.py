import shutil
import subprocess
from pathlib import Path

import docker
import click

from jaypore_ci.config import const


def _run():
    print("Reading environment variables.")
    client = docker.from_env()
    # Get environment from secrets
    env = {}
    if const.env:
        env.update(
            {
                line.split("=", 1)[0]: line.split("=", 1)[1]
                for line in subprocess.check_output(
                    (
                        "bash -c '"
                        "source /jaypore_ci/repo/secrets/bin/set_env.sh "
                        f"{const.env} && env'"
                    ),
                    shell=True,
                )
                .decode()
                .strip()
                .split("\n")
                if line.startswith("JAYPORE_")
            }
        )
    env["REPO_SHA"] = const.repo_sha
    env["REPO_ROOT"] = const.repo_root
    env["ENV"] = const.env
    # Run job with environment set
    for pipe in Path("/jaypore_ci/run/cicd/config").glob("*.py"):
        print(f"Running pipeline: {pipe.name}", end="")
        container = client.containers.run(
            image=f"im_jayporeci__pipe__{const.repo_sha}",
            command=f"python3 {pipe}",
            name=f"jayporeci__pipe__{pipe.name[:-3]}__{const.repo_sha}",
            environment=env,
            volumes=[
                f"/tmp/jayporeci__src__{const.repo_sha}:/jaypore_ci/run",
                "/var/run/docker.sock:/var/run/docker.sock",
            ],
            working_dir="/jaypore_ci/run",
            detach=True,
        )
        print("\t: ", container.id)


def _build():
    print(f"Building docker image for SHA: {const.repo_sha}")
    client = docker.from_env()
    # Copy repo to build so that we can add an extra dockerfile
    shutil.copytree("/jaypore_ci/repo", "/jaypore_ci/build")
    with open("/jaypore_ci/build/cicd/Dockerfile", "w", encoding="utf-8") as fl:
        fl.write(
            f"""
            FROM    arjoonn/jci:{const.version}
            COPY    ./ /jaypore_ci/repo/
            RUN     cd /jaypore_ci/repo/ && git clean -fdx
            """
        )
    # Build the image
    im_tag = f"im_jayporeci__pipe__{const.repo_sha}"
    client.images.build(
        path="/jaypore_ci/build",
        dockerfile="cicd/Dockerfile",
        tag=im_tag,
        pull=True,
    )
    # Copy the clean files to a shared volume so that jobs can use that.
    client.containers.run(
        image=im_tag,
        command="cp -r /jaypore_ci/repo/. /jaypore_ci/run",
        volumes=[
            f"/tmp/jayporeci__src__{const.repo_sha}:/jaypore_ci/run",
        ],
    )
    print("Build complete: ", im_tag)


# ---------------
# Cli subcommands
# ---------------


@click.group()
def cli():
    "Jaypore CI"


@cli.command()
def build():
    """
    Build an iamge containing a snapshot of the given repo at the current commit.
    """
    _build()


@cli.command()
def run():
    """
    Run all the pipelines available inside the `cicd/configs` folder.
    """
    _run()


@cli.command()
def hook():
    _build()
    _run()


_hook_cmd = """

        export ENV=ci
        export REPO_SHA=$(git rev-parse HEAD)
        export REPO_ROOT=$(git rev-parse --show-toplevel)
        docker build -t jci $REPO_ROOT
        docker run \
            -e ENV \
            -e REPO_SHA \
            -e REPO_ROOT \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v $REPO_ROOT:/jaypore_ci/repo:ro \
            -v /tmp/jayporeci__src__$REPO_SHA:/jaypore_ci/run \
            -d \
            arjoonn/jci:{const.version} hook
    """


@cli.command()
def hook_cmd():
    f"""
    Please add the following to your *.git/hooks/pre-push* file in order to
    trigger the CI system.

    .. code-block:: bash
    {_hook_cmd}

    .. note::
        Please make sure that you change the ENV value to what you need.
    """
    print(_hook_cmd)


if __name__ == "__main__":
    cli()
