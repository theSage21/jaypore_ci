import os
import shutil
from pathlib import Path

import docker
import click

from jaypore_ci.config import const


def _run():
    client = docker.from_env()
    client.containers.run(
        image=f"im_jayporeci__pipe__{const.repo_sha}",
        command="python3 /jaypore_ci/run/cicd/main.py",
        name=f"jayporeci__pipe__{const.repo_sha}",
        environment={"REPO_SHA": const.repo_sha},
        volumes=[
            f"/tmp/jayporeci__src__{const.repo_sha}:/jaypore_ci/run",
            "/tmp/jayporeci__cidfiles:/jaypore_ci/cidfiles:ro",
            "/var/run/docker.sock/var/run/docker.sock",
        ],
        working_dir="/jaypore_ci/run",
        detach=True,
    )


def _build():
    client = docker.from_env()
    shutil.copytree("/jaypore_ci/repo", "/jaypore_ci/build")
    with open("/jaypore_ci/build/cicd/Dockerfile", "w", encoding="utf-8") as fl:
        fl.write(
            f"""
            FROM arjoonn/jci:{const.version}
            COPY ./ /jaypore_ci/repo/
            """
        )
    client.images.build(
        path="/jaypore_ci/build",
        dockerfile="cicd/Dockerfile",
        tag=f"im_jayporeci__pipe__{const.repo_sha}",
        pull=True,
    )


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


if __name__ == "__main__":
    cli()
