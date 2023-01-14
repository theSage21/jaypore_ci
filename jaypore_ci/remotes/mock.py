"""
A gitea remote git host.

This is used to report pipeline status to the remote.
"""
import os


from jaypore_ci.interfaces import Remote
from jaypore_ci.logging import logger


class Mock(Remote):  # pylint: disable=too-many-instance-attributes
    """
    A mock remote implementation.
    """

    @classmethod
    def from_env(cls):
        return cls(branch=os.environ["JAYPORE_BRANCH"], sha=os.environ["JAYPORE_SHA"])

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
