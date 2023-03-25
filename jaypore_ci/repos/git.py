import re
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
        remote = cls._parse_remote_url(remote_url=cls._get_git_remote_url())
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
        return (
            subprocess.check_output(
                "git remote -v | grep push | head -n1 | awk '{print $2}'", shell=True
            )
            .decode()
            .strip()
        )

    @classmethod
    def _parse_remote_url(cls, remote_url: str) -> str:
        """
        Parses remote URL and validates it.
        """
        if "@" in remote_url:
            remote_url = cls._convert_ssh_to_https(remote_url)
        assert (
            "https://" in remote_url and ".git" in remote_url
        ), f"Only https & ssh remotes are supported. (Remote: {remote_url})"
        return remote_url

    @classmethod
    def _convert_ssh_to_https(cls, url: str) -> str:
        """
        Converts ssh URL into https.
        """
        ssh_url_pattern = r".+@(?P<uri>.+):(?P<path>.+\.git)"
        m = re.match(ssh_url_pattern, url)
        assert m, f"Failed to parse ssh URL to https! (URL: {url})"
        return f"https://{m.group('uri')}/{m.group('path')}"
