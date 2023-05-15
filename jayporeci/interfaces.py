from typing import NamedTuple, Set, Dict, Any
from enum import Enum


class Status(Enum):
    """
    Used to define status of jobs and pipelines.
    """

    PENDING = "p"
    RUNNING = "r"
    SUCCESS = "s"
    FAILURE = "f"

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
    A named group for any set of jobs.
    Stages are executed in order of their definition.
    """

    name: str
    pipeline: "Pipeline"
    kwargs: Dict[Any, Any]


class Job(NamedTuple):
    """
    A job is a declarative definition of

    - What we want to do
    - When to do it
    - What to do after completing it
    - How to do it
    """

    name: str
    command: str
    is_service: bool
    pipeline: "Pipeline"
    status: Status
    image: str
    stage: Stage
    kwargs: Dict[Any, Any]


class Edge(NamedTuple):
    """
    An edge connects two jobs and always has a kind.
    It also carries with it a set of kwargs that a Scheduler can use to
    determine if the edge can be followed.
    """

    kind: str
    frm: Job
    to: Job
    kwargs: Dict[Any, Any]


class Pipeline(NamedTuple):
    """
    A pipeline is a set of jobs and edges.
    """

    jobs: Set[Job]
    edges: Set[Edge]
    kwargs: Dict[Any, Any]


class Scheduler(NamedTuple):
    """
    A Scheduler takes a pipeline along with an instance of an executor and
    performs a walk on the graph defined by the pipeline using the executor.
    """
