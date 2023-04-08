import shutil
import subprocess
from pathlib import Path

import docker
import click

from jaypore_ci.config import const

__MAX_WIDTH__ = 75


def tell(msg, detail=""):
    "Inform a user about something"
    FIRST_COL = 30
    SECOND_COL = __MAX_WIDTH__ - FIRST_COL
    msg = msg + (" " * FIRST_COL)
    detail = str(detail) + (" " * SECOND_COL)
    lines = [
        msg[:FIRST_COL],
        "|" if msg.strip() else "",
        detail[:SECOND_COL],
    ]
    print(" ".join(lines)[:__MAX_WIDTH__], "┃")


def _run():
    tell(f"Read secrets/{const.env}.enc")
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
        tell("Start pipeline", pipe.name)
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
        tell("", container.id)


def _build():
    tell("Build repo image", f"sha: {const.repo_sha}")
    client = docker.from_env()
    # Copy repo to build so that we can add an extra dockerfile
    shutil.copytree("/jaypore_ci/repo", "/jaypore_ci/build")
    with open("/jaypore_ci/build/cicd/Dockerfile", "w", encoding="utf-8") as fl:
        fl.write(
            f"""
            FROM    {const.image}
            RUN     touch /jaypore_ci && rm -rf /jaypore_ci
            COPY    ./ /jaypore_ci/repo/
            RUN     cd /jaypore_ci/repo/ && git clean -fdx
            RUN     ls /jaypore_ci
            ENTRYPOINT ["/bin/bash", "-l", "-c"]
            """
        )
    with open("/jaypore_ci/build/cicd/copy_tree.sh", "w", encoding="utf-8") as fl:
        fl.write(
            """
            echo $PWD
            ls /jaypore_ci
            cp -r  /jaypore_ci/repo/. /jaypore_ci/run
            """
        )
    # Build the image
    im_tag = f"im_jayporeci__pipe__{const.repo_sha}"
    client.images.build(
        path="/jaypore_ci/build",
        dockerfile="cicd/Dockerfile",
        tag=im_tag,
        pull=const.image != "jci",  # are we in debug mode?
    )
    tell("Copy repo code")
    # Copy the clean files to a shared volume so that jobs can use that.
    logs = client.containers.run(
        im_tag,
        # command="echo startcopy && cp -r /jaypore_ci/repo/. /jaypore_ci/run && ls /jaypore_ci/run && echo endcopy",
        command="ls -alR /jaypore_ci/repo",
        volumes=[f"/tmp/jayporeci__src__{const.repo_sha}:/jaypore_ci/run"],
        working_dir="/jaypore_ci",
        remove=False,
        stdout=True,
        stderr=True,
    )
    print(logs.decode())
    tell("Repo image built", im_tag)


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
    print("━━━━━━━━━━━┓")
    print("Jaypore CI ┃")
    print((("━━━━━━━━━━━┻" + ("━" * __MAX_WIDTH__))[:__MAX_WIDTH__]) + "━┓")
    _build()
    _run()
    print(("━" * (__MAX_WIDTH__ + 1)) + "┛")


_hook_cmd = """

        export ENV=ci
        export REPO_SHA=$(git rev-parse HEAD)
        export REPO_ROOT=$(git rev-parse --show-toplevel)
        docker run \
            -e ENV \
            -e REPO_SHA \
            -e REPO_ROOT \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v $REPO_ROOT:/jaypore_ci/repo:ro \
            -v /tmp/jayporeci__src__$REPO_SHA:/jaypore_ci/run \
            -d \
            {const.image} hook
    """


def wrapdoc(fn):
    fn.__doc__ = f"""
    Please add the following to your *.git/hooks/pre-push* file in order to
    trigger the CI system.

    .. note::
        Please make sure that you change the ENV value to what you need.

    .. code-block:: bash
    {_hook_cmd}
    """
    return fn


@cli.command()
@wrapdoc
def hook_cmd():
    print(_hook_cmd)


if __name__ == "__main__":
    cli()
