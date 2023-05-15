"""
A mock remote.

This is used to test pipelines.
"""
from jaypore_ci.interfaces import Remote, Repo
from jaypore_ci.logging import logger


class Mock(Remote):  # pylint: disable=too-many-instance-attributes
    """
    A mock remote implementation.
    """

    @classmethod
    def from_env(cls, *, repo: Repo):
        return cls(branch=repo.branch, sha=repo.sha)

    def logging(self):
        """
        Return's a logging instance with information about gitea bound to it.
        """
        return logger.bind(branch=self.branch)

    def get_pr_id(self):
        """
        Returns the pull request ID for the current branch.
        """
        return self.branch

    def publish(self, report: str, status: str):
        """
        Will publish the report to the remote.
        """
        pr_id = self.get_pr_id()
        self.logging().debug(
            "Published report", report=report, status=status, pr_id=pr_id
        )
