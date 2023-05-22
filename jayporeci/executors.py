"""
A docker executor for Jaypore CI.
"""
import json
import subprocess
from enum import Enum
from copy import deepcopy
from typing import NamedTuple, Dict, List, Tuple, Any

import pendulum
from rich import print as rprint


from . import definitions as defs


def run(args: List[str] | str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """
    Add common options for subprocess calls.
    """
    kwargs["shell"] = True
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.STDOUT
    kwargs["check"] = False
    return subprocess.run(args, **kwargs)


class NameKind(Enum):
    NET = "net"
    JOB = "job"
    JCI = "jci"

    @classmethod
    def parse(cls, kind: str) -> "NameKind":
        return {"net": NameKind.NET, "job": NameKind.JOB, "jci": NameKind.JCI}[kind]


class Name(NamedTuple):
    """
    Name for things:

        - jayporeci__net__<sha>
        - jayporeci__jci__<sha>
        - jayporeci__job__<sha>__<jobname>
    """

    raw: str
    sha: str
    kind: NameKind
    job_name: str | None = None
    prefix: str = "jayporeci"
    sep: str = "__"

    @classmethod
    def parse(cls, name: str) -> "Name" | None:
        if not name.startswith(f"{cls.prefix}{cls.sep}"):
            return None
        _, kind, *parts = name.split(cls.sep)
        kind = NameKind.parse(kind)
        if len(parts) == 1:
            return cls(raw=name, sha=parts[0], kind=kind)
        if len(parts) == 2:
            return cls(raw=name, sha=parts[0], job_name=parts[1], kind=kind)
        return None

    @classmethod
    def create(cls, *, kind: NameKind, sha: str, job_name: str | None = None) -> "Name":
        raw = None
        if kind == NameKind.NET:
            raw = cls.sep.join([cls.prefix, str(kind), sha])
        if kind == NameKind.JOB:
            assert job_name is not None
            raw = cls.sep.join([cls.prefix, str(kind), sha, job_name])
        if kind == NameKind.JCI:
            raw = cls.sep.join([cls.prefix, str(kind), sha])
        assert raw is not None
        return Name(kind=kind, sha=sha, job_name=job_name, raw=raw)

    def get_related(self, kind: NameKind) -> str:
        return self.sep.join([self.prefix, str(kind), self.sha])


class DockerExecutor(defs.Executor):
    """
    Run jobs via docker.
    This executor requires a `sha` to be given to it and it will run everything
    by isolating it within this `SHA` value.

    Using this executor will:
        - Create a separate namespace for each run.
        - Run jobs as part of the namespace.
        - Create and use networks within this namespace.
        - Clean up everything when the pipeline exits.
    """

    def __init__(self, sha: str) -> None:
        super().__init__()
        self.sha = sha
        self.__execution_order__: List[Tuple[str | None, str, str]] = []

    def teardown(self) -> None:
        self.delete_run_network()
        self.delete_run_jobs()

    def setup(self) -> None:
        self.delete_old_containers()

    def delete_old_containers(self) -> None:
        too_old = pendulum.now().subtract(days=defs.const.retain_old_jobs_n_days)
        names_to_remove = set()
        for container in run("docker ps -f status=exited --format json").stdout.split():
            container = json.loads(container)
            name = Name.parse(container["Names"])
            if name is None or name.sha == self.sha:
                # Non-Jaypore CI containers and containers for this sha
                continue
            finished_at = pendulum.parse(container["CreatedAt"])
            if finished_at <= too_old:
                names_to_remove.add(name)
        spaced_names = " ".join(name.raw for name in names_to_remove)
        run(f"docker container rm -v {spaced_names}")
        # Remove networks
        net_ids = [name.sep.join([name.prefix, name.sha]) for name in names_to_remove]
        pipes = " ".join([f"-f name={net_id}" for net_id in net_ids])
        net_ids = (
            run(f"docker network ls {pipes} --format 'table {{.ID}}'").stdout.split(
                "\n"
            )
        )[1:]
        net_ids = " ".join(net_ids)
        run(f"docker network rm {net_ids}")

    def create_network(self) -> None:
        """
        Will create a docker network.

        If it fails to do so in 3 attempts it will raise an
        exception and fail.
        """
        name = Name.create(kind=NameKind.NET, sha=self.sha)
        for _ in range(3):
            if (
                len(run(f"docker network ls -f name={name.raw}").stdout.split("\n"))
                != 1
            ):
                # self.logging().info("Found network", network_name=self.get_net())
                return
            run(f"docker network create -d bridge {name.raw}")
            # self.logging().info( "Create network",)
        raise Exception("Cannot create network")

    def delete_run_jobs(self) -> None:
        """
        Deletes all jobs associated with the pipeline for this
        executor.

        It will stop any jobs that are still running.
        """
        names_to_remove = set()
        for container in run("docker ps --format json").stdout.split():
            container = json.loads(container)
            name = Name.parse(container["Names"])
            if name is not None and name.sha == self.sha:
                names_to_remove.add(name)
        names = " ".join(name.raw for name in names_to_remove)
        run(f"docker stop -t 5 {names}")

    def delete_run_network(self) -> None:
        """
        Delete the network for this executor run.
        """
        name = Name.create(kind=NameKind.NET, sha=self.sha)
        run(f"docker network rm {name.raw}")

    def run(self, job: defs.Job) -> str:
        """
        Run the given job and return a docker container ID.
        In case something goes wrong it will raise TriggerFailed
        """
        # Build env
        env = {}
        env["REPO_SHA"] = self.sha
        env["ENV"] = defs.const.env
        cmd = ["docker", "run", "--detach"]
        for key, val in env.items():
            cmd += ["-e", f"{key}={val}"]
        cmd += [
            "-v",
            "/var/run/docker.sock:/var/run/docker.sock",
            "-v",
            f"/tmp/jayporeci__src__{self.sha}:/jayporeci/run",
        ]
        name = Name.create(kind=NameKind.JOB, sha=self.sha, job_name=job.name)
        cmd += [
            "--name",
            name.raw,
            "--network",
            name.get_related(NameKind.NET),
        ]
        if not job.is_service:
            cmd += ["--workdir", "/jayporeci/run"]
        cmd += [job.image]
        if job.command:
            cmd += [job.command]
        rprint(cmd)
        container_id: str = run(cmd).stdout.strip()
        self.__execution_order__.append((name.job_name, container_id, "Run"))
        return container_id

    def get_status(self, run_id: str) -> defs.JobState:
        """
        Given a run_id, it will get the status for that run.
        """
        inspect = run(f"docker inspect {run_id}").stdout.strip()
        inspect = json.loads(inspect)
        is_running = inspect["State"]["Status"] == "running"
        exit_code = int(inspect["State"]["ExitCode"])
        status = defs.Status.RUNNING
        if not is_running:
            status = defs.Status.SUCCESS if exit_code == 0 else defs.Status.FAILURE
        state = defs.JobState(
            run_id=run_id,
            is_running=is_running,
            exit_code=exit_code,
            status=status,
            logs="",
            started_at=pendulum.parse(inspect["State"]["StartedAt"]),
            finished_at=pendulum.parse(inspect["State"]["FinishedAt"])
            if inspect["State"]["FinishedAt"] != "0001-01-01T00:00:00Z"
            else None,
        )
        # --- logs
        logs = run(f"docker logs {run_id}").stdout.strip()
        return state._replace(logs=logs)

    def get_execution_order(self) -> Dict[str, int]:
        return {
            name: i
            for i, (name, *_) in enumerate(self.__execution_order__)
            if name is not None
        }
