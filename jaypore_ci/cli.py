import os
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
    # Run job with environment set
    for pipe in Path("/jaypore_ci/run/cicd/config").glob("*.py"):
        print(f"Running pipeline: {pipe.name}", end="")
        container = client.containers.run(
            image=f"im_jayporeci__pipe__{const.repo_sha}",
            command=f"python3 {pipe}",
            name=f"jayporeci__pipe__{pipe.name[:-3]}__{const.repo_sha}",
            environment={
                "REPO_SHA": const.repo_sha,
                "REPO_ROOT": const.repo_root,
                "ENV": const.env,
                **env,
            },
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


@cli.command()
def activate():
    """
    When a repository is freshly cloned the git hooks are not set so this
    command is used to set the git hooks for that repo.
    """
    print(
        """
        echo "
        docker run \\
            -e ENV=ci \\
            -e REPO_SHA=$(git rev-parse HEAD) \\
            -e REPO_ROOT=$(git rev-parse --show-toplevel) \\
            -v /var/run/docker.sock:/var/run/docker.sock \\
            -v $(git rev-parse --show-toplevel):/jaypore_ci/repo:ro \\
            jci hook
    """
    )


if __name__ == "__main__":
    cli()
