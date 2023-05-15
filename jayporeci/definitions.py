"""
This module holds definitions that are used throughtout Jaypore CI.

It also holds configuration information that is obtained from the environment.
"""
import os
from enum import Enum
import importlib.metadata
from pathlib import Path
from urllib.parse import urlparse
from typing import NamedTuple, Any, List, Tuple

import tomllib


class Version(NamedTuple):
    """
    Semantic versioning for Jaypore CI
    """

    major: int
    minor: int
    patch: int
    trail: str = None

    def __repr__(self):
        if self.trail:
            return f"{self.major}.{self.minor}.{self.patch}-{self.trail}"
        return f"{self.major}.{self.minor}.{self.patch}"

    def __str__(self):
        return self.__repr__()

    @classmethod
    def parse(cls, inp: str) -> "Version":
        if inp is None or inp == "":
            return None
        trail = None
        major, minor, patch = inp.split(".")
        major = major[1:] if major[0].lower() == "v" else major
        assert major.isdigit()
        assert minor.isdigit()
        if "-" in patch:
            patch, trail = patch.split("-", 1)
            assert patch.isdigit()
        return cls(major=int(major), minor=int(minor), patch=int(patch), trail=trail)


def get_version() -> Version:
    """
    Try to find out what version JayporeCI is running.
    """
    try:
        return Version.parse(importlib.metadata.version(__package__ or __name__))
    except importlib.metadata.PackageNotFoundError:
        try:
            with open((Path(__file__) / "../../pyproject.toml").resolve(), "rb") as fl:
                data = tomllib.load(fl)
            return Version.parse(data["tool"]["poetry"]["version"])
        except FileNotFoundError:
            return None


class Const(NamedTuple):
    """
    Constants that do not change.
    They are defined here in order to be DRY.
    """

    jci: str = "JayporeCI"
    version: Version = get_version()
    repo_root: str = os.environ.get("REPO_ROOT")
    repo_sha: str = os.environ.get("REPO_SHA")
    env: str = os.environ.get("ENV")
    # image: str = f"arjoonn/jci:{version}"


const = Const()


# ================
# Definitions
# ================


class Status(Enum):
    """
    Used to define status of :class:`~jayporeci.definitions.Job`s and
    :class:`~jayporeci.definitions.Pipeline`s.
    """

    PENDING = 0
    RUNNING = 5
    SUCCESS = 10
    FAILURE = 15

    def is_terminal(self):
        return self in (Status.SUCCESS, Status.FAILURE)

    def get_dot(self):
        if self == Status.SUCCESS:
            return "🟢"
        if self == Status.FAILURE:
            return "🔴"
        if self == Status.RUNNING:
            return "🔵"
        return "🟡"


class Stage(NamedTuple):
    """
    A :class:`~jayporeci.definitions.Job` always belongs to a stage.
    Stages are executed in order of their declaration.
    """

    name: str
    jobs: Tuple["Job"] = None
    edges: Tuple["Edge"] = None
    kwargs: Tuple[Tuple[Any, Any]] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def has_job(self, name):
        for job in self.jobs or []:
            if job.name == name:
                return True
        return False

    def add_edge(
        self,
        *,
        frm_name: str,
        to_name: str,
        kind: "EdgeKind",
        kwargs: Tuple[Tuple[Any, Any]] = None,
    ) -> "Stage":
        frm = None
        for job in self.jobs or []:
            if job.name == frm_name:
                frm = job
                break
        assert frm is not None, f"Job not found: {frm_name}"
        to = None
        for job in self.jobs or []:
            if job.name == to_name:
                to = job
                break
        assert to is not None, f"Job not found: {to_name}"
        edges = set([] if self.edges is None else self.edges)
        edges.add(Edge(kind=kind, frm=frm, to=to, kwargs=kwargs or tuple()))
        return self._replace(edges=tuple(edges))


class Job(NamedTuple):
    """
    A Job is a declarative definition of

    - What we want to do
    - When to do it
    - What to do after completing it
    - How to do it
    """

    name: str
    command: str
    is_service: bool
    state: "JobState"
    image: str
    kwargs: Tuple[Tuple[Any, Any]] = None


class EdgeKind(Enum):
    ALL_SUCCESS = "all"


class Edge(NamedTuple):
    """
    An edge connects two jobs and always has a kind.
    It also carries with it a set of kwargs that a Scheduler can use to
    determine if the edge can be followed.
    """

    kind: EdgeKind
    frm: Job
    to: Job
    kwargs: Tuple[Tuple[Any, Any]] = None


class Pipeline(NamedTuple):
    """
    A pipeline is a set of jobs and edges.
    """

    repo: "Repo"
    stages: Tuple[Stage] = None
    kwargs: Tuple[Tuple[Any, Any]] = None


class Scheduler:
    """
    A Scheduler takes a pipeline along with an instance of an executor and
    performs a walk on the graph defined by the pipeline using the executor.
    """

    def __init__(self, *, pipeline, executor, platform, reporter) -> "Scheduler":
        self.pipeline: "Pipeline" = pipeline
        self.executor: "Executor" = executor
        self.platform: "Platform" = platform
        self.reporter: "Reporter" = reporter
        self.__run_on_exit__ = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.__run_on_exit__:
            self.run()
        return False

    def job(self) -> "Scheduler":
        """
        Creates a :class:`~jayporeci.definitions.Job` instance based on the
        pipeline/stage that it is being defined in. See

        :class:`~jayporeci.definitions.Job` for details on what parameters can be
        passed to this function.
        """
        return self

    def run(self) -> None:
        """
        Run the scheduler.

        This is called automatically when the context
        of the scheduler declaration finishes.

        It is usually a simple loop of:

            - Given (self.pipeline, self.executor)
            - Issue new executor command
            - Loop

        The scheduler will try to do a complete "walk" of the pipeline, based
        on how jobs are declared and connected.
        """


# ---- ======================
# ---- supporting definitions
# ---- ======================


class RemoteInfo(NamedTuple):
    """
    Holds information about the remote.
    Can be ssh / https.
    """

    netloc: str
    owner: str
    repo: str
    original: str

    @classmethod
    def parse(cls, remote: str) -> "RemoteInfo":
        """
        Given a git remote url string, parses and breaks down information
        contained in the url.

        Works with the following formats:

            ssh://git@gitea.arjoonn.com:arjoonn/jaypore_ci.git
            ssh+git://git@gitea.arjoonn.com:arjoonn/jaypore_ci.git

            git@gitea.arjoonn.com:arjoonn/jaypore_ci.git

            https://gitea.arjoonn.com/midpath/jaypore_ci.git
            http://gitea.arjoonn.com/midpath/jaypore_ci.git
        """
        original = remote
        if (
            ("ssh://" in remote or "ssh+git://" in remote or "://" not in remote)
            and "@" in remote
            and remote.endswith(".git")
        ):
            _, remote = remote.split("@")
            netloc, path = remote.split(":")
            owner, repo = path.split("/")
            return RemoteInfo(
                netloc=netloc,
                owner=owner,
                repo=repo.replace(".git", ""),
                original=original,
            )
        url = urlparse(remote)
        return RemoteInfo(
            netloc=url.netloc,
            owner=Path(url.path).parts[1],
            repo=Path(url.path).parts[2].replace(".git", ""),
            original=original,
        )


class Repo:
    """
    Contains information about the current VCS repo.
    Currently only supports Git.
    """

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


class JobState(NamedTuple):
    status: Status
    is_running: bool
    exit_code: int
    logs: str
    started_at: str
    finished_at: str


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
        On exit the executor MUST clean up any pending / stuck / zombie jobs
        that are still there.
        """

    def get_status(self, run_id: str) -> JobState:
        """
        Returns the status of a given run.
        """
        raise NotImplementedError()


class Platform:
    """
    Something that allows us to show other people the status of the CI job.
    It could be gitea / github / gitlab / email.
    """

    def publish(self, report: str, status: str):
        """
        Publish this report somewhere.
        """
        raise NotImplementedError()

    def setup(self) -> None:
        """
        This function is meant to perform any work that should be done before
        running the pipeline.
        """

    def teardown(self) -> None:
        """
        This function will be called once the pipeline is finished.
        """

    @classmethod
    def from_env(cls, *, repo: "Repo") -> "Platform":
        """
        This function should create a :class:`~jayporeci.definitions.Platform"
        instance from the given :class:`~jayporeci.definitions.Repo`

        It can read git information from disk / look at environment variables etc.
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
