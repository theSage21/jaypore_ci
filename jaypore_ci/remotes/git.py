"""
This is used to save the pipeline status to git itself.
"""
import time
import subprocess

from jaypore_ci.interfaces import Remote
from jaypore_ci.repos import Git
from jaypore_ci.logging import logger


class GitRemote(Remote):  # pylint: disable=too-many-instance-attributes
    """
    You can save pipeline status to git using this remote.

    To push/fetch your local refs to a git remote you can run

    .. code-block:: console

        git fetch   origin refs/jayporeci/*:refs/jayporeci/*
        git push    origin refs/jayporeci/*:refs/jayporeci/*
    """

    @classmethod
    def from_env(cls, *, repo: Git) -> "GitRemote":
        """
        Creates a remote instance from the environment.
        """
        assert isinstance(repo, Git), "Git remote can only work in a git repo"
        return cls(
            repo=repo,
            branch=repo.branch,
            sha=repo.sha,
        )

    def __init__(self, *, repo, **kwargs):
        super().__init__(**kwargs)
        self.repo = repo

    def logging(self):
        """
        Return's a logging instance with information about git bound to it.
        """
        return logger.bind(repo=self.repo)

    def publish(self, report: str, status: str) -> None:
        """
        Will publish the report via email.

        :param report: Report to write to remote.
        :param status: One of ["pending", "success", "error", "failure",
            "warning"] This is the dot next to each commit in gitea.
        """
        assert status in ("pending", "success", "error", "failure", "warning")
        now = time.time()
        lines = ""
        git_blob_sha = subprocess.check_output(
            "git hash-object -w --stdin",
            input=report,
            text=True,
            stderr=subprocess.STDOUT,
            shell=True,
        ).strip()
        lines += f"\n100644 blob {git_blob_sha}\t{now}.txt"
        lines = lines.strip()
        git_tree_sha = subprocess.run(
            "git mktree",
            input=lines,
            text=True,
            shell=True,
            check=False,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        git_commit_sha = subprocess.run(
            f"git commit-tree {git_tree_sha}",
            text=True,
            input=f"JayporeCI status: {now}",
            shell=True,
            check=False,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        assert git_commit_sha.returncode == 0
        git_commit_sha = (
            subprocess.check_output(
                f"git update-ref refs/jayporeci/{self.repo.sha} {git_commit_sha.stdout.strip()}",
                shell=True,
                stderr=subprocess.STDOUT,
            )
            .decode()
            .strip()
        )
        self.logging().info(
            "Published status to local git: refs/jayporeci/{self.repo.sha} {git_commit_sha}"
        )
