"""
A gitea remote git host.

This is used to report pipeline status to the remote.
"""
import os

import requests

from jaypore_ci.interfaces import Remote, RemoteApiFailed, Repo, RemoteInfo
from jaypore_ci.logging import logger


class Gitea(Remote):  # pylint: disable=too-many-instance-attributes
    """
    The remote implementation for gitea.
    """

    @classmethod
    def from_env(cls, *, repo: Repo) -> "Gitea":
        """
        Creates a remote instance from the environment.
        It will:

            - Find the remote location using `git remote`.
            - Find the current branch
            - Create a new pull request for that branch
            - Allow posting updates using the gitea token provided
        """
        os.environ["JAYPORE_COMMIT_BRANCH"] = repo.branch
        os.environ["JAYPORE_COMMIT_SHA"] = repo.sha
        rem = RemoteInfo.parse(repo.remote)
        return cls(
            root=f"https://{rem.netloc}",
            owner=rem.owner,
            repo=rem.repo,
            branch=repo.branch,
            token=os.environ["JAYPORE_GITEA_TOKEN"],
            sha=repo.sha,
        )

    def __init__(
        self, *, root, owner, repo, token, **kwargs
    ):  # pylint: disable=too-many-arguments
        super().__init__(**kwargs)
        # --- customer
        self.root = root
        self.api = f"{root}/api/v1"
        self.owner = owner
        self.repo = repo
        self.token = token
        self.timeout = 10
        self.base_branch = "develop"
        # ---
        self.__pr_id__ = None

    def logging(self):
        """
        Return's a logging instance with information about gitea bound to it.
        """
        return logger.bind(
            root=self.root, owner=self.owner, repo=self.repo, branch=self.branch
        )

    def get_pr_id(self):
        """
        Returns the pull request ID for the current branch.
        """
        if self.__pr_id__ is None:
            r = requests.post(
                f"{self.api}/repos/{self.owner}/{self.repo}/pulls",
                params={"access_token": self.token},
                timeout=self.timeout,
                json={
                    "base": self.base_branch,
                    "body": "Branch auto created by JayporeCI",
                    "head": self.branch,
                    "title": self.branch,
                },
            )
            self.logging().debug("Get PR Id", status_code=r.status_code)
            if r.status_code == 409:
                self.__pr_id__ = r.text.split("issue_id:")[1].split(",")[0].strip()
                return self.get_pr_id()
            if r.status_code == 201:
                return self.get_pr_id()
            if (
                r.status_code == 404
                and r.json()["message"] == "IsBranchExist"
                and self.base_branch != "main"
            ):
                self.base_branch = "main"
                return self.get_pr_id()
            self.logging().debug(
                "Failed gitea api",
                api=self.api,
                owner=self.owner,
                repo=self.repo,
                token=self.token,
                branch=self.branch,
                status=r.status_code,
                response=r.text,
            )
            raise RemoteApiFailed(r)
        return self.__pr_id__

    def publish(self, report: str, status: str):
        """
        Will publish the report to the remote.

        :param report: Report to write to remote.
        :param status: One of ["pending", "success", "error", "failure",
            "warning"] This is the dot next to each commit in gitea.
        """
        assert status in ("pending", "success", "error", "failure", "warning")
        issue_id = self.get_pr_id()
        # Get existing PR body
        r = requests.get(
            f"{self.api}/repos/{self.owner}/{self.repo}/pulls/{issue_id}",
            timeout=self.timeout,
            params={"access_token": self.token},
        )
        self.logging().debug("Get existing body", status_code=r.status_code)
        assert r.status_code == 200
        body = r.json()["body"]
        body = (line for line in body.split("\n"))
        prefix = []
        for line in body:
            if "```jayporeci" in line:
                prefix = prefix[:-1]
                break
            prefix.append(line)
        while prefix and prefix[-1].strip() == "":
            prefix = prefix[:-1]
        prefix.append("")
        # Post new body with report
        report = "\n".join(prefix) + "\n" + report
        r = requests.patch(
            f"{self.api}/repos/{self.owner}/{self.repo}/pulls/{issue_id}",
            data={"body": report},
            timeout=self.timeout,
            params={"access_token": self.token},
        )
        self.logging().debug("Published new report", status_code=r.status_code)
        # Set commit status
        r = requests.post(
            f"{self.api}/repos/{self.owner}/{self.repo}/statuses/{self.sha}",
            json={
                "context": "JayporeCi",
                "description": f"Pipeline status is: {status}",
                "state": status,
                "target_url": f"{self.root}/{self.owner}/{self.repo}/pulls/{issue_id}",
            },
            timeout=self.timeout,
            params={"access_token": self.token},
        )
        self.logging().debug(
            "Published new status", status=status, status_code=r.status_code
        )
