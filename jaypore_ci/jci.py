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

from jaypore_ci import remotes, executors, reporters
from jaypore_ci.interfaces import Remote, Executor, Reporter, TriggerFailed, Status
from jaypore_ci.logging import logger

TZ = "UTC"

__all__ = ["Pipeline", "Job"]


# All of these statuses are considered "finished" statuses
FIN_STATUSES = (Status.FAILED, Status.PASSED, Status.TIMEOUT, Status.SKIPPED)
PREFIX = "JAYPORE_"


class Job:  # pylint: disable=too-many-instance-attributes
    """
    This is the fundamental building block.
    Each job goes through a lifecycle defined by `Status` class.

    A job is run by an Executor as part of a Pipeline.
    """

    def __init__(
        self,
        name: str,
        command: Union[str, Callable],
        pipeline: "Pipeline",
        *,
        status: str = None,
        image: str = None,
        timeout: int = None,
        env: dict = None,
        children: List["Job"] = None,
        parents: List["Job"] = None,
        is_service: bool = False,
        stage: str = None,
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

    def update_report(self):
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
        try:
            self.pipeline.remote.publish(report, status)
        except Exception as e:  # pylint: disable=broad-except
            self.logging().exeception(e)
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
                    job_run = e.args[0]
                    self.logging().error(
                        "Trigger failed",
                        returncode=job_run.returncode,
                        job_name=self.name,
                    )
                    logs = job_run.stdout.decode()
                    self.logs["stdout"] = reporters.clean_logs(logs)
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

    def is_complete(self):
        """
        Is this job complete? It could have passed/ failed etc.
        We no longer need to check for updates in a complete job.
        """
        return self.status in FIN_STATUSES

    def get_env(self):
        """
        Gets the environment variables for a given job by interpolating it with
        the pipeline's environment.
        """
        return {
            **{
                k[len(PREFIX) :]: v
                for k, v in os.environ.items()
                if k.startswith(PREFIX)
            },
            **self.pipeline.pipe_kwargs.get("env", {}),
            **self.env,
        }


class Pipeline:  # pylint: disable=too-many-instance-attributes
    """
    A pipeline acts as a controlling/organizing mechanism for multiple jobs.

    - Each pipeline has stages. A default stage of 'Pipeline' is always available.
    - Stages are executed in order. Execution proceeds to the next stage ONLY
      if all jobs in a stage have passed.
    - Jobs can be defined inside stages.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        remote: Remote = None,
        executor: Executor = None,
        reporter: Reporter = None,
        *,
        graph_direction: str = "TB",
        poll_interval: int = 1,
        **kwargs,
    ) -> "Pipeline":
        self.jobs = {}
        self.services = []
        self.should_pass_called = set()
        self.remote = remote if remote is not None else remotes.gitea.Gitea.from_env()
        self.executor = executor if executor is not None else executors.docker.Docker()
        self.reporter = reporter if reporter is not None else reporters.text.Text()
        self.graph_direction = graph_direction
        self.poll_interval = poll_interval
        self.executor.set_pipeline(self)
        self.stages = ["Pipeline"]
        # ---
        kwargs["image"] = kwargs.get("image", "arjoonn/jaypore_ci:latest")
        kwargs["timeout"] = kwargs.get("timeout", 15 * 60)
        kwargs["env"] = kwargs.get("env", {})
        kwargs["stage"] = "Pipeline"
        self.pipe_kwargs = kwargs
        self.stage_kwargs = None

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
        self.executor.__enter__()
        self.remote.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.run()
        self.executor.__exit__(exc_type, exc_value, traceback)
        self.remote.__exit__(exc_type, exc_value, traceback)
        return False

    def get_status(self):
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

    def get_status_dot(self):
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
        Declare a job in this pipeline.

        Jobs inherit their keyword arguments from the stage they are defined in
        and the pipeline they are defined in.

        Initially jobs are in a `PENDING` state.
        """
        depends_on = [] if depends_on is None else depends_on
        depends_on = [depends_on] if isinstance(depends_on, str) else depends_on
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

    def env_matrix(self, **kwargs):
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
        Run the pipeline. This is almost always called automatically when the
        context of the pipeline declaration finishes.
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
        assert name not in self.jobs, "Stage name cannot match a job's name"
        assert name not in self.stages, "Stage names cannot be re-used"
        self.stages.append(name)
        kwargs["stage"] = name
        self.stage_kwargs = kwargs
        yield  # -------------------------
        self.stage_kwargs = None
