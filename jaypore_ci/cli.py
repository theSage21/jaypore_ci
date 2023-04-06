import docker
import click

from jaypore_ci.config import const


@click.group()
def cli():
    "Cli commands for Jaypore CI"
    pass


@cli.command()
def build():
    """
    Build an iamge containing a snapshot of the given repo at the current commit.
    """
    client = docker.from_env()
    client.images.build(
        path=f"{const.repo_root}/cicd/Dockerfile",
        tag=f"im_jayporeci__pipe__{const.repo_sha}",
        buildargs={"JAYPORECI_VERSION": const.expected_version},
    )


@cli.command()
def run():
    # docker run \
    # -d \
    # --cidfile /tmp/jayporeci__cidfiles/$SHA \
    # --workdir /jaypore_ci/run \
    # im_jayporeci__pipe__$SHA \
    # bash -c "ENV=$ENV bash /jaypore_ci/repo/$JAYPORE_CODE_DIR/cli.sh run"
    # echo '----------------------------------------------'
    # }
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


if __name__ == "__main__":
    cli()
