import os
import subprocess
from typing import List

from jaypore_ci.interfaces import Repo


class Git(Repo):
    def files_changed(self, target: str) -> List[str]:
        "Returns list of files changed between current sha and target"
        return (
            subprocess.check_output(
                f"git diff --name-only {target} {self.sha}", shell=True
            )
            .decode()
            .strip()
            .split("\n")
        )

    @classmethod
    def from_env(cls) -> "Git":
        """
        Gets repo status from the environment and git repo on disk.
        """
        remote = cls._get_remote_url()
        assert remote, "Obtained remote url for pushing is empty!"
        branch = (
            subprocess.check_output(
                r"git branch | grep \* | awk '{print $2}'", shell=True
            )
            .decode()
            .strip()
        )
        sha = subprocess.check_output("git rev-parse HEAD", shell=True).decode().strip()
        message = (
            subprocess.check_output("git log -1 --pretty=%B", shell=True)
            .decode()
            .strip()
        )
        return cls(sha=sha, branch=branch, remote=remote, commit_message=message)

    @classmethod
    def _get_remote_url(cls) -> str:
        if os.environ.get("JAYPORECI_DOCS_EXAMPLES_TEST_MODE", False):
            return "https://test-mode.com/test/test-remote.git"
        return (
            subprocess.check_output(
                "git remote -v | grep push | head -n1 | awk '{print $2}'", shell=True
            )
            .decode()
            .strip()
        )
