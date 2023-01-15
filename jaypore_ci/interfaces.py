"""
Defines interfaces for remotes and executors.

Currently only gitea and docker are supported as remote and executor
respectively.
"""
from enum import Enum


class TriggerFailed(Exception):
    "Failure to trigger a job"


class Status(Enum):
    "Each pipeline can be in any one of these statuses"
    PENDING = 10
    RUNNING = 30
    FAILED = 40
    PASSED = 50
    TIMEOUT = 60
    SKIPPED = 70


class Executor:
    """
    It could be docker / podman / shell etc.
    Something that allows us to run a job.

    Must define `__enter__` and `__exit__` so that it can be used as a context
    manager.
    """

    def run(self, job: "Job") -> str:
        "Run a job and return it's ID"
        raise NotImplementedError()

    def __init__(self):
        self.pipe_id = None
        self.pipeline = None

    def set_pipeline(self, pipeline):
        """Set the current pipeline to the given one."""
        self.pipe_id = id(pipeline)
        self.pipeline = pipeline

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class Remote:
    """
    It could be gitea / github / gitlab / email system.
    Something that allows us to post the status of the CI.

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
        raise NotImplementedError()


class Reporter:
    """
    Something that allows us to report the status of a pipeline
    """

    def render(self, pipeline):
        """
        Render a report for the pipeline.
        """
        raise NotImplementedError()
