import time
import re
from enum import Enum
from itertools import product
from collections import defaultdict, namedtuple
from typing import List, Union, Callable

import structlog
import pendulum

from jaypore_ci import gitea, docker
from jaypore_ci.interfaces import Remote, Executor
from jaypore_ci.logging import logger, jaypore_logs

TZ = "UTC"


class Status(Enum):
    "Each pipeline can be in these statuses"
    PENDING = 10
    RUNNING = 30
    FAILED = 40
    PASSED = 50
    TIMEOUT = 60
    SKIPPED = 70


# All of these statuses are considered "finished" statuses
FIN_STATUSES = (Status.FAILED, Status.PASSED, Status.TIMEOUT, Status.SKIPPED)

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_logs(logs):
    logs = logs.replace("<", r"\<").replace(">", r"\>")
    return ansi_escape.sub("", logs)


class Job:  # pylint: disable=too-many-instance-attributes
    """
    This is the fundamental building block.
    Each job goes through a lifecycle defined by `Status` class.
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
    ):
        self.name = name
        self.command = command
        self.image = image
        self.status = status
        self.timeout = timeout
        self.pipeline = pipeline
        self.env = env
        self.children = children if children is not None else []
        self.parents = parents if parents is not None else []
        self.is_service = is_service
        # --- run information
        self.logs = defaultdict(list)
        self.job_id = id(self)
        self.run_id = None
        self.run_start = None
        self.last_check = None

    def logging(self):
        return self.pipeline.logging().bind(
            job_id=self.job_id,
            job_name=self.name,
            run_id=self.run_id,
        )

    def update_report(self):
        """
        Update the report
        Usually called when a job changes some of it's internal state like:
            - logs
            - status
            - last_check
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
        self.pipeline.remote.publish(self.pipeline.render_report(), status)

    def should_pass(self, *, is_internal_call=False):
        """
        This is the main thing. It allows you to run assertions on the job like:
            assert job.should_pass()

        This function will block until the status of the job is known.
        It will also trigger and monitor all jobs required to obtain the status
        for this job.
        """
        self.logging().info("Ok called")
        if not is_internal_call:
            self.pipeline.should_pass_called.add(self)
        self.trigger()
        if self.is_service:
            self.status = Status.PASSED
            self.logging().info("Service started successfully", status=self.status)
        else:
            self.monitor_until_completion()
            self.logging().info("Ok finished", status=self.status)
        self.update_report()
        return self.status == Status.PASSED

    def monitor_until_completion(self):
        while not self.is_complete():
            self.check_job()
            time.sleep(1)
            now = pendulum.now(TZ)
            if (now - self.run_start).in_seconds() > self.timeout:
                self.status = Status.TIMEOUT
                self.logging().error(
                    "Timeout", seconds_elapsed=(now - self.run_start).in_seconds()
                )
                self.update_report()
                break
        self.check_job()

    def get_graph(self):
        """
        Given the current job, builds a graph of all jobs that are it's
        parents.

        Returns a set of nodes & edges.
        """
        nodes = set([self])
        edges = set()
        for parent in self.parents:
            edges.add((parent, self))
            if parent not in nodes:
                p_nodes, p_edges = parent.get_graph()
                nodes |= set(p_nodes)
                edges |= set(p_edges)
        return list(sorted(nodes, key=lambda x: x.name)), list(
            sorted(edges, key=lambda x: (x[0].name, x[1].name))
        )

    def trigger(self):
        """
        Trigger the job via the pipeline's executor.
        This will immediately return and will not wait for the job to finish.
        """
        if self.status == Status.PENDING:
            self.run_start = pendulum.now(TZ)
            self.logging().info("Trigger called")
            self.status = Status.RUNNING
            if isinstance(self.command, str):
                self.run_id = self.pipeline.executor.run(self)
            else:
                self.run_id = f"pyrun_{self.job_id}"
                self.command(self)
            self.logging().info("Trigger done")
        else:
            self.logging().info("Trigger called but job already running")
        self.check_job()

    def check_job(self, with_update_report=True):
        self.logging().debug("Checking job run")
        if isinstance(self.command, str):
            is_running, exit_code, logs = self.pipeline.executor.get_status(self.run_id)
            self.last_check = pendulum.now(TZ)
            self.logging().debug(
                "Job run status found", is_running=is_running, exit_code=exit_code
            )
            if is_running:
                self.status = Status.RUNNING if not self.is_service else Status.PASSED
            else:
                self.status = Status.PASSED if exit_code == 0 else Status.FAILED
            logs = clean_logs(logs)
            log_lines = logs.split("\n")
            for line in log_lines[len(self.logs["stdout"]) :]:
                self.logging().debug(
                    f">>> {line.strip()}",
                    job_name=self.name,
                    run_id=self.run_id,
                )
            self.logs["stdout"] = log_lines
            if with_update_report:
                self.update_report()

    def is_complete(self):
        return self.status in FIN_STATUSES

    def get_env(self):
        return {**self.pipeline.env, **self.env}


class Pipeline:  # pylint: disable=too-many-instance-attributes
    """
    A pipeline acts as a controlling mechanism for multiple jobs.
    We can use a pipeline to define:

        - Running order of jobs. If they are to be run in sequence or in parallel.
        - Common environment / timeout / configuration details.
        - Where all to publish the CI report.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        remote: Remote = None,
        executor: Executor = None,
        image: str = "python:3.11",
        timeout: int = 15 * 60,
        env: dict = None,
        *,
        graph_direction: str = "TB",
    ) -> "Pipeline":
        self.image = image
        self.timeout = timeout
        self.env = {} if env is None else env
        self.jobs = []
        self.services = []
        self.should_pass_called = set()
        self.remote = remote if remote is not None else gitea.Gitea.from_env()
        self.executor = executor if executor is not None else docker.Docker()
        self.graph_direction = graph_direction
        self.executor.set_pipe_id(id(self), self)

    def logging(self):
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
        self.executor.__exit__(exc_type, exc_value, traceback)
        self.remote.__exit__(exc_type, exc_value, traceback)
        return False

    def get_status(self):
        pipe_status = Status.PENDING
        for job in self.jobs:
            if job.status == Status.RUNNING:
                pipe_status = Status.RUNNING
                break
        for service in self.services:
            service.check_job(with_update_report=False)
        service.check_job()
        for job in self.should_pass_called:
            if job.is_complete():
                pipe_status = job.status
                break
        return pipe_status

    def get_status_dot(self):
        if self.get_status() == Status.PASSED:
            return "🟢"
        if self.get_status() in (Status.FAILED, Status.TIMEOUT):
            return "🔴"
        if self.get_status() == Status.SKIPPED:
            return "🔵"
        return "🟡"

    def render_report(self):
        return f"""
<details>
    <summary>JayporeCi: {self.get_status_dot()} {self.remote.sha[:10]}</summary>

{self.render_graph()}
{self.render_logs()}

</details>"""

    def render_graph(self) -> str:
        mermaid = ""
        for job in self.should_pass_called:
            nodes, edges = job.get_graph()
            mermaid += f"""
```mermaid
graph {self.graph_direction}
"""
            ref = {n: f"N{i}" for i, n in enumerate(nodes)}
            st_map = {
                Status.PENDING: "pending",
                Status.RUNNING: "running",
                Status.FAILED: "failed",
                Status.PASSED: "passed",
                Status.TIMEOUT: "timeout",
                Status.SKIPPED: "skipped",
            }

            for a, b in edges:
                mermaid += f"""
        {ref[a]}({a.name}):::{st_map[a.status]} --> {ref[b]}({b.name}):::{st_map[b.status]}"""
            mermaid += """



        classDef pending fill:#aaa, color:black, stroke:black,stroke-width:2px,stroke-dasharray: 5 5;
        classDef skipped fill:#aaa, color:black, stroke:black,stroke-width:2px;
        classDef assigned fill:#ddd, color:black, stroke:black,stroke-width:2px;
        classDef running fill:#bae1ff,color:black,stroke:black,stroke-width:2px,stroke-dasharray: 5 5;
        classDef passed fill:#88d8b0, color:black, stroke:black;
        classDef failed fill:#ff6f69, color:black, stroke:black;
        classDef timeout fill:#ffda9e, color:black, stroke:black;
``` """
        return mermaid

    def render_logs(self):
        all_logs = []
        fake_job = namedtuple("fake_job", "name logs")(
            "JayporeCi", {"stdout": jaypore_logs}
        )
        for job in [fake_job] + self.jobs:
            job_log = []
            for logname, stream in job.logs.items():
                job_log += [f"============== {logname} ============="]
                job_log += [line.strip() for line in stream]
            if job_log:
                all_logs += [
                    "- <details>",
                    f"    <summary>Logs: {job.name}</summary>",
                    "",
                    "    ```",
                    *[f"    {line}" for line in job_log],
                    "    ```",
                    "",
                    "  </details>",
                ]
        return "\n".join(all_logs)

    def job(
        self,
        *commands: List[str],
        name: str,
        image: str = None,
        timeout: int = None,
        env: dict = None,
        is_service: bool = False,
    ) -> Job:
        if not is_service:
            assert commands
        job = Job(
            name=name if name is not None else " ",
            command="\n".join(commands),
            status=Status.PENDING,
            image=image if image is not None else self.image,
            timeout=timeout if timeout is not None else self.timeout,
            pipeline=self,
            env=env if env is not None else {},
            children=[],
            is_service=is_service,
        )
        self.jobs.append(job)
        if is_service:
            self.services.append(job)
        return job

    def in_parallel(self, *jobs, image=None, timeout=None, env=None):
        jobs = [job for job in jobs if job is not None]
        timeout = (
            max(
                job.timeout if job.timeout is not None else self.timeout for job in jobs
            )
            if timeout is None
            else timeout
        )

        def run_and_join(job_self):
            job_self.logs["stdout"].append("Starting parallel run")
            for job in jobs:
                job_self.logs["stdout"].append(f"Trigger job: {job.job_id} {job.name}")
                job.trigger()
            something_is_running = True
            while something_is_running:
                time.sleep(1)
                something_is_running = False
                for job in jobs:
                    job.check_job(with_update_report=False)
                    job_self.logs["stdout"].append(
                        f"Checking: {job.job_id} {job.name} is_complete: {job.is_complete()}"
                    )
                    if not job.is_complete():
                        something_is_running = True
                    if (
                        job.is_complete()
                        and job.status != Status.PASSED
                        and job_self.status == Status.RUNNING
                    ):
                        job_self.status = Status.FAILED
                        msg = "Dependent job failed"
                        job_self.logging().error(msg, failed_job_id=job.job_id)
                        job_self.logs["stdout"].append(f"{msg}: {job.job_id}")
                job.check_job()
            if job_self.status == Status.RUNNING:
                job_self.status = Status.PASSED
                job_self.logs["stdout"].append("Ok")

        join = Job(
            name="+",
            command=run_and_join,
            status=Status.PENDING,
            image=self.image if image is None else image,
            pipeline=self,
            env={} if env is None else env,
            children=[],
            timeout=timeout,
            parents=list(jobs),
        )
        self.jobs.append(join)
        for job in jobs:
            job.children.append(join)
        return join

    def in_sequence(self, *jobs, image=None, env=None, timeout=None):
        jobs = [job for job in jobs if job is not None]

        def run_seq(job_self):
            job_self.logs["stdout"].append("Starting sequential run")
            for job in jobs:
                if job_self.status == Status.RUNNING:
                    job_self.logs["stdout"].append(
                        f"Running job: {job.job_id} {job.name}"
                    )
                    ok = job.should_pass(is_internal_call=True)
                    if not ok:
                        job_self.status = Status.FAILED
                        job_self.logs["stdout"].append(
                            f"Failed job: {job.job_id} {job.name}"
                        )
                        job_self.logging().error(
                            "Dependent job failed", failed_job_id=job.job_id
                        )
                elif job_self.status == Status.FAILED:
                    job_self.logs["stdout"].append(
                        f"Skipping job: {job.job_id} {job.name}"
                    )
                    job.status = Status.SKIPPED
                    continue
            if job_self.status == Status.RUNNING:
                job_self.status = Status.PASSED
                job_self.logs["stdout"].append("Ok")

        last_job = None
        for job in jobs:
            if last_job is not None:
                last_job.children.append(job)
                job.parents.append(last_job)
            last_job = job
        # final chain job
        timeout = (
            sum(
                job.timeout if job.timeout is not None else self.timeout for job in jobs
            )
            if timeout is None
            else timeout
        )
        join = Job(
            name="+",
            command=run_seq,
            status=Status.PENDING,
            image=self.image if image is None else image,
            pipeline=self,
            env={} if env is None else env,
            children=[],
            timeout=timeout,
            parents=[last_job],
        )
        self.jobs.append(join)
        last_job.children.append(join)
        return join

    def env_matrix(self, **kwargs):
        """
        Return a cartesian product of all the provided kwargs
        """
        keys = list(sorted(kwargs.keys()))
        for values in product(*[kwargs[key] for key in keys]):
            yield dict(list(zip(keys, values)))
