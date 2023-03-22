"""
Defines interfaces for remotes and executors.

Currently only gitea and docker are supported as remote and executor
respectively.
"""
from enum import Enum
from typing import NamedTuple, List


class TriggerFailed(Exception):
    "Failure to trigger a job"


class RemoteApiFailed(Exception):
    "Failure while working with a remote"


class JobStatus(NamedTuple):
    is_running: bool
    exit_code: int
    logs: str
    started_at: str
    finished_at: str


class Status(Enum):
    "Each pipeline can ONLY be in any one of these statuses"
    PENDING = 10
    RUNNING = 30
    FAILED = 40
    PASSED = 50
    TIMEOUT = 60
    SKIPPED = 70


class Repo:
    """
    Contains information about the current VCS repo.
    """

    def __init__(self, sha: str, branch: str, remote: str, commit_message: str):
        self.sha: str = sha
        self.branch: str = branch
        self.remote: str = remote
        self.commit_message: str = commit_message

    def files_changed(self, target: str) -> List[str]:
        """
        Returns list of file paths that have changed between current sha and
        target.
        """
        raise NotImplementedError()

    @classmethod
    def from_env(cls) -> "Repo":
        """
        Creates a :class:`~jaypore_ci.interfaces.Repo` instance
        from the environment and git repo on disk.
        """
        raise NotImplementedError()


class Executor:
    """
    An executor is something used to run a job.
    It could be docker / podman / shell etc.
    """

    def run(self, job: "Job") -> str:
        "Run a job and return it's ID"
        raise NotImplementedError()

    def __init__(self):
        self.pipe_id = None
        self.pipeline = None

    def set_pipeline(self, pipeline: "Pipeline") -> None:
        """Set the current pipeline to the given one."""
        self.pipe_id = id(pipeline)
        self.pipeline = pipeline

    def setup(self) -> None:
        """
        This function is meant to perform any work that should be done before
        running any jobs.
        """

    def teardown(self) -> None:
        """
        On exit the executor must clean up any pending / stuck / zombie jobs that are still there.
        """

    def get_status(self, run_id: str) -> JobStatus:
        """
        Returns the status of a given run.
        """
        raise NotImplementedError()


class Remote:
    """
    Something that allows us to show other people the status of the CI job.
    It could be gitea / github / gitlab / email system.
    """

    def __init__(self, *, sha, branch):
        self.sha = sha
        self.branch = branch

    def publish(self, report: str, status: str):
        """
        Publish this report somewhere.
        """
        raise NotImplementedError()

    def setup(self) -> None:
        """
        This function is meant to perform any work that should be done before
        running any jobs.
        """

    def teardown(self) -> None:
        """
        This function will be called once the pipeline is finished.
        """

    @classmethod
    def from_env(cls, *, repo: "Repo"):
        """
        This function should create a Remote instance from the given environment.
        It can read git information / look at environment variables etc.
        """
        raise NotImplementedError()


class Reporter:
    """
    Something that generates the status of a pipeline.

    It can be used to generate reports in markdown, plaintext, html, pdf etc.
    """

    def render(self, pipeline: "Pipeline") -> str:
        """
        Render a report for the pipeline.
        """
        raise NotImplementedError()
