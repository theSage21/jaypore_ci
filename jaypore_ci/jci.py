"""
The code submodule for Jaypore CI.
"""
import time
import os
from itertools import product
from collections import defaultdict
from typing import List, Union, Callable
from contextlib import contextmanager

import structlog
import pendulum

from jaypore_ci.exceptions import BadConfig
from jaypore_ci.config import const
from jaypore_ci.changelog import version_map
from jaypore_ci import remotes, executors, reporters, repos, clean
from jaypore_ci.interfaces import (
    Remote,
    Executor,
    Reporter,
    TriggerFailed,
    Status,
    Repo,
)
from jaypore_ci.logging import logger

TZ = "UTC"

__all__ = ["Pipeline", "Job"]


# All of these statuses are considered "finished" statuses
FIN_STATUSES = (Status.FAILED, Status.PASSED, Status.TIMEOUT, Status.SKIPPED)
PREFIX = "JAYPORE_"

# Check if we need to upgrade Jaypore CI
def ensure_version_is_correct():
    """
    Ensure that the version of Jaypore CI that is running, the code inside
    cicd.py, and pre-push.sh are at compatible versions.

    If versions do not match then this function will print out instructions on
    what to do in order to upgrade.

    Downgrades are not allowed, you need to re-install that specific version.
    """
    if (
        const.expected_version is not None
        and const.version is not None
        and const.expected_version != const.version
    ):
        print("Expected : ", const.expected_version)
        print("Got      : ", const.version)
        if const.version > const.expected_version:
            print(
                "Your current version is higher than the expected one. Please "
                "re-install Jaypore CI in this repo as downgrades are not "
                "supported."
            )
        if const.version < const.expected_version:
            print("--- Upgrade Instructions ---")
            for version in sorted(version_map.keys()):
                if version < const.version or version > const.expected_version:
                    continue
                for line in version_map[version]["instructions"]:
                    print(line)
            print("--- -------------------- ---")
        raise BadConfig(
            "Version mismatch between arjoonn/jci:<tag> docker container and pre-push.sh script"
        )


class Job:  # pylint: disable=too-many-instance-attributes
    """
    This is the fundamental building block for running jobs.
    Each job goes through a lifecycle defined by
    :class:`~jaypore_ci.interfaces.Status`.

    A job is run by an :class:`~jaypore_ci.interfaces.Executor` as part of a
    :class:`~jaypore_ci.jci.Pipeline`.

    It is never created manually. The correct way to create a job is to use
    :meth:`~jaypore_ci.jci.Pipeline.job`.

    :param name:            The name for the job. Names must be unique across
                            jobs and stages.
    :param command:         The command that we need to run for the job. It can
                            be set to `None` when `is_service` is True.
    :param is_service:      Is this job a service or not? Service jobs are
                            assumed to be
                            :class:`~jaypore_ci.interfaces.Status.PASSED` as
                            long as they start.  They are shut down when the
                            entire pipeline has finished executing.
    :param pipeline:        The pipeline this job is associated with.
    :param status:          The :class:`~jaypore_ci.interfaces.Status` of this job.
    :param image:           What docker image to use for this job.
    :param timeout:         Defines how long a job is allowed to run before being
                            killed and marked as
                            class:`~jaypore_ci.interfaces.Status.FAILED`.
    :param env:             A dictionary of environment variables to pass to
                            the docker run command.
    :param children:        Defines which jobs depend on this job's output
                            status.
    :param parents:         Defines which jobs need to pass before this job can
                            be run.
    :param stage:           What stage the job belongs to. This stage name must
                            exist so that we can assign jobs to it.
    :param executor_kwargs: A dictionary of keyword arguments that the executor
                            can use when running a job. Different executors may
                            use this in different ways, for example with the
                            :class:`~jaypore_ci.executors.docker.Docker`
                            executor this may be used to run jobs with
                            `--add-host or --device
                            <https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run>`_
                            .
    """

    def __init__(
        self,
        name: str,
        command: Union[str, Callable],
        pipeline: "Pipeline",
        *,
        status: str = None,
        children: List["Job"] = None,
        parents: List["Job"] = None,
        is_service: bool = False,
        stage: str = None,
        # --- executor kwargs
        image: str = None,
        timeout: int = None,
        env: dict = None,
        executor_kwargs: dict = None,
    ):
        self.name = name
        self.command = command
        self.image = image
        self.status = status
        self.run_state = None
        self.timeout = timeout
        self.pipeline = pipeline
        self.env = env
        self.children = children if children is not None else []
        self.parents = parents if parents is not None else []
        self.is_service = is_service
        self.stage = stage
        self.executor_kwargs = executor_kwargs if executor_kwargs is not None else {}
        # --- run information
        self.logs = defaultdict(list)
        self.job_id = id(self)
        self.run_id = None
        self.run_start = None
        self.last_check = None

    def logging(self):
        """
        Returns a logging instance that has job specific information bound to
        it.
        """
        return self.pipeline.logging().bind(
            job_id=self.job_id,
            job_name=self.name,
            run_id=self.run_id,
        )

    def update_report(self) -> str:
        """
        Update the status report. Usually called when a job changes some of
        it's internal state like when logs are updated or when status has
        changed.
        """
        self.logging().debug("Update report")
        status = {
            Status.PENDING: "pending",
            Status.RUNNING: "pending",
            Status.FAILED: "failure",
            Status.PASSED: "success",
            Status.TIMEOUT: "warning",
            Status.SKIPPED: "warning",
        }[self.pipeline.get_status()]
        report = self.pipeline.reporter.render(self.pipeline)
        with open("/jaypore_ci/run/jaypore_ci.status.txt", "w", encoding="utf-8") as fl:
            fl.write(report)
        self.pipeline.remote.publish(report, status)
        return report

    def trigger(self):
        """
        Trigger the job via the pipeline's executor.
        This will immediately return and will not wait for the job to finish.

        It is also idempotent. Calling this multiple times will only trigger
        the job once.
        """
        if self.status == Status.PENDING:
            self.run_start = pendulum.now(TZ)
            self.logging().info("Trigger called")
            self.status = Status.RUNNING
            if isinstance(self.command, str):
                try:
                    self.run_id = self.pipeline.executor.run(self)
                    self.logging().info("Trigger done")
                except TriggerFailed as e:
                    self.logging().error(
                        "Trigger failed",
                        error=e,
                        job_name=self.name,
                    )
                    self.status = Status.FAILED
        else:
            self.logging().info("Trigger called but job already running")
        self.check_job()

    def check_job(self, *, with_update_report=True):
        """
        This will check the status of the job.
        If `with_update_report` is False, it will not push an update to the remote.
        """
        if isinstance(self.command, str) and self.run_id is not None:
            self.logging().debug("Checking job run")
            self.run_state = self.pipeline.executor.get_status(self.run_id)
            self.last_check = pendulum.now(TZ)
            self.logging().debug(
                "Job run status found",
                is_running=self.run_state.is_running,
                exit_code=self.run_state.exit_code,
            )
            if self.run_state.is_running:
                self.status = Status.RUNNING if not self.is_service else Status.PASSED
            else:
                self.status = (
                    Status.PASSED if self.run_state.exit_code == 0 else Status.FAILED
                )
            self.logs["stdout"] = reporters.clean_logs(self.run_state.logs)
            if with_update_report:
                self.update_report()

    def is_complete(self) -> bool:
        """
        Is this job complete? It could have passed/ failed etc.
        We no longer need to check for updates in a complete job.
        """
        return self.status in FIN_STATUSES

    def get_env(self):
        """
        Gets the environment variables for a given job.
        Order of precedence for setting values is:

        1. Pipeline
        2. Stage
        3. Job
        """
        env = {
            k[len(PREFIX) :]: v for k, v in os.environ.items() if k.startswith(PREFIX)
        }
        env.update(self.pipeline.pipe_kwargs.get("env", {}))
        env.update(self.env)  # Includes env specified in stage kwargs AND job kwargs
        return env


class Pipeline:  # pylint: disable=too-many-instance-attributes
    """
    A pipeline acts as a controlling/organizing mechanism for multiple jobs.

    :param repo:            Provides information about the codebase.
    :param reporter:        Provides reports based on the state of the pipeline.
    :param remote:          Allows us to publish reports to somewhere like gitea/email.
    :param executor:        Runs the specified jobs.
    :param poll_interval:   Defines how frequently (in seconds) to check the
                            pipeline status and publish a report.
    """

    # We need a way to avoid actually running the examples. Something like a
    # "dry-run" option so that only the building of the config is done and it's
    # never actually run. It might be a good idea to make this an actual config
    # variable but I'm not sure if we should do that or not.
    __run_on_exit__ = True

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        repo: Repo = None,
        remote: Remote = None,
        executor: Executor = None,
        reporter: Reporter = None,
        poll_interval: int = 10,
        **kwargs,
    ) -> "Pipeline":
        self.jobs = {}
        self.services = []
        self.should_pass_called = set()
        self.repo = repo if repo is not None else repos.Git.from_env()
        self.remote = (
            remote
            if remote is not None
            else remotes.gitea.Gitea.from_env(repo=self.repo)
        )
        self.executor = executor if executor is not None else executors.docker.Docker()
        self.reporter = reporter if reporter is not None else reporters.text.Text()
        self.poll_interval = poll_interval
        self.stages = ["Pipeline"]
        self.__pipe_id__ = None
        self.executor.set_pipeline(self)
        # ---
        kwargs["image"] = kwargs.get("image", "arjoonn/jci")
        kwargs["timeout"] = kwargs.get("timeout", 15 * 60)
        kwargs["env"] = kwargs.get("env", {})
        kwargs["stage"] = "Pipeline"
        self.pipe_kwargs = kwargs
        self.stage_kwargs = None

    @property
    def pipe_id(self):
        if self.__pipe_id__ is None:
            self.__pipe_id__ = self.__get_pipe_id__()
        return self.__pipe_id__

    def __get_pipe_id__(self):
        """
        This is mainly here so that during testing we can override this and
        provide a different way to get the pipe id
        """
        with open(f"/jaypore_ci/cidfiles/{self.repo.sha}", "r", encoding="utf-8") as fl:
            return fl.read().strip()

    def logging(self):
        """
        Return a logger with information about the current pipeline bound to
        it.
        """
        return logger.bind(
            **{
                **structlog.get_context(self.remote.logging()),
                **structlog.get_context(self.executor.logging()),
                "pipe_id": id(self),
            }
        )

    def __enter__(self):
        ensure_version_is_correct()
        self.executor.setup()
        self.remote.setup()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if Pipeline.__run_on_exit__:
            self.run()
            self.executor.teardown()
            self.remote.teardown()
        return False

    def get_status(self) -> Status:
        """
        Calculates a pipeline's status based on the status of it's jobs.
        """
        for job in self.jobs.values():
            if job.status == Status.RUNNING:
                return Status.RUNNING
        service = None
        for service in self.services:
            service.check_job(with_update_report=False)
        if service is not None:
            service.check_job(with_update_report=False)
        has_pending = False
        for job in self.jobs.values():
            job.check_job(with_update_report=False)
            if not job.is_complete():
                has_pending = True
            else:
                if job.status != Status.PASSED:
                    return Status.FAILED
        return Status.PENDING if has_pending else Status.PASSED

    def get_status_dot(self) -> str:
        """
        Get's the status dot for the pipeline.
        """
        if self.get_status() == Status.PASSED:
            return "🟢"
        if self.get_status() == Status.FAILED:
            return "🔴"
        if self.get_status() == Status.SKIPPED:
            return "🔵"
        return "🟡"

    def job(
        self,
        name: str,
        command: str,
        *,
        depends_on: List[str] = None,
        **kwargs,
    ) -> Job:
        """
        Creates a :class:`~jaypore_ci.jci.Job` instance based on the
        pipeline/stage that it is being defined in. See
        :class:`~jaypore_ci.jci.Job` for details on what parameters can be
        passed to the job.
        """
        depends_on = [] if depends_on is None else depends_on
        depends_on = [depends_on] if isinstance(depends_on, str) else depends_on
        name = clean.name(name)
        assert name, "Name should have some value after it is cleaned"
        assert name not in self.jobs, f"{name} already defined"
        assert name not in self.stages, "Stage name cannot match a job's name"
        kwargs, job_kwargs = dict(self.pipe_kwargs), kwargs
        kwargs.update(self.stage_kwargs if self.stage_kwargs is not None else {})
        kwargs.update(job_kwargs)
        if not kwargs.get("is_service"):
            assert command, f"Command: {command}"
        job = Job(
            name=name if name is not None else " ",
            command=command,
            status=Status.PENDING,
            pipeline=self,
            children=[],
            parents=depends_on,
            **kwargs,
        )
        for parent_name in depends_on:
            assert (
                parent_name in self.jobs
            ), f"Parent job has to be defined before a child. Cannot find {parent_name}"
            parent = self.jobs[parent_name]
            assert parent.stage == job.stage, "Cannot have dependencies across stages"
        self.jobs[name] = job
        if kwargs.get("is_service"):
            self.services.append(job)
        return job

    @classmethod
    def env_matrix(cls, **kwargs):
        """
        Return a cartesian product of all the provided kwargs.
        """
        keys = list(sorted(kwargs.keys()))
        for values in product(*[kwargs[key] for key in keys]):
            yield dict(list(zip(keys, values)))

    def __ensure_duplex__(self):
        for name, job in self.jobs.items():
            for parent_name in job.parents:
                parent = self.jobs[parent_name]
                parent.children = list(sorted(set(parent.children).union(set([name]))))

    def run(self):
        """
        Run the pipeline. This is always called automatically when the context
        of the pipeline declaration finishes and so unless you are doing
        something fancy you don't need to call this manually.
        """
        self.__ensure_duplex__()
        # Run stages one by one
        job = None
        for stage in self.stages:
            # --- Trigger starting jobs
            jobs = {name: job for name, job in self.jobs.items() if job.stage == stage}
            for name in {job.name for job in jobs.values() if not job.parents}:
                jobs[name].trigger()
            # --- monitor and ensure all jobs run
            while not all(job.is_complete() for job in jobs.values()):
                for job in jobs.values():
                    job.check_job(with_update_report=False)
                    if not job.is_complete():
                        # If all dependencies are met: trigger
                        if len(job.parents) == 0 or all(
                            jobs[parent_name].is_complete()
                            and jobs[parent_name].status == Status.PASSED
                            for parent_name in job.parents
                        ):
                            job.trigger()
                        elif any(
                            jobs[parent_name].is_complete()
                            and jobs[parent_name].status != Status.PASSED
                            for parent_name in job.parents
                        ):
                            job.status = Status.SKIPPED
                job.check_job()
                time.sleep(self.poll_interval)
            # --- has this stage passed?
            if not all(
                job.is_complete() and job.status == Status.PASSED
                for job in jobs.values()
            ):
                self.logging().error("Stage failed")
                job.update_report()
                break
        self.logging().error("Pipeline passed")
        if job is not None:
            report = job.update_report()
            self.logging().info("Report:", report=report)

    @contextmanager
    def stage(self, name, **kwargs):
        """
        A stage in a pipeline.

        Any kwargs passed to this stage are supplied to jobs created within
        this stage.
        """
        name = clean.name(name)
        assert name, "Name should have some value after it is cleaned"
        assert name not in self.jobs, "Stage name cannot match a job's name"
        assert name not in self.stages, "Stage names cannot be re-used"
        self.stages.append(name)
        kwargs["stage"] = name
        self.stage_kwargs = kwargs
        yield  # -------------------------
        self.stage_kwargs = None
