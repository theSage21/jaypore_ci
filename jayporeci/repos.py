import subprocess
from typing import Dict, List, Union, Any
from . import definitions as defs


class GitRepo(defs.Repo):
    """
    Interact with a given git repository.
    """

    def __init__(self, sha: str, branch: str, remote: str, commit_message: str):
        self.sha: str = sha
        self.branch: str = branch
        self.remote: str = remote
        self.commit_message: str = commit_message

    def __repr__(self):
        sha = f"{self.sha}"[:8]
        return f"GitRepo <{sha}: {self.branch}>"

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
        remote = (
            subprocess.check_output(
                "git remote -v | grep push | head -n1 | grep https | awk '{print $2}'",
                shell=True,
            )
            .decode()
            .strip()
        )
        assert "https://" in remote, f"Only https remotes supported: {remote}"
        assert ".git" in remote
        # NOTE: Later on perhaps we should support non-https remotes as well
        # since JCI does not actually do anything with the remote.
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
