"""
Defines interfaces for remotes and executors.

Currently only gitea and docker are supported as remote and executor
respectively.
"""
from enum import Enum


class TriggerFailed(Exception):
    "Failure to trigger a job"


class Status(Enum):
    "Each pipeline can ONLY be in any one of these statuses"
    PENDING = 10
    RUNNING = 30
    FAILED = 40
    PASSED = 50
    TIMEOUT = 60
    SKIPPED = 70


class Executor:
    """
    An executor is something used to run a job.
    It could be docker / podman / shell etc.

    It must define `__enter__` and `__exit__` so that it can be used as a context manager.

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        On exit the executor must clean up any pending / stuck / zombie jobs that are still there.
        """


class Remote:
    """
    Something that allows us to show other people the status of the CI job.
    It could be gitea / github / gitlab / email system.

    Must define `__enter__` and `__exit__` so that it can be used as a context
    manager.
    """

    def __init__(self, *, sha, branch):
        self.sha = sha
        self.branch = branch

    def publish(self, report: str, status: str):
        """
        Publish this report somewhere.
        """
        raise NotImplementedError()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @classmethod
    def from_env(cls):
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
