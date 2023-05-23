import shutil
import subprocess
from pathlib import Path
from typing import Any

import click

from jayporeci import definitions as defs


def tell(msg: str, detail: str = "") -> None:
    """
    Inform a user about something via the CLI.
    """
    FIRST_COL = 30
    SECOND_COL = defs.const.max_cli_width - FIRST_COL
    msg = msg + (" " * FIRST_COL)
    detail = detail + (" " * SECOND_COL)
    lines = [
        msg[:FIRST_COL],
        "┃" if msg.strip() else "│",
        detail[:SECOND_COL],
    ]
    print(" ".join(lines)[: defs.const.max_cli_width], "┃")


@click.command()
def cli():
    """
    Build and run Jaypore CI pipeline
    """
    cmd = f""" bash -c '
            echo "
                from jci
                add . /jayporeci/repo
                " | docker build \
                -t jayporeci__run__{defs.const.repo_sha} \
                -f=- \
                . \
        '
        """
    print(cmd)
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        check=False,
    )
    print(proc.stdout.decode())


if __name__ == "__main__":
    cli()
