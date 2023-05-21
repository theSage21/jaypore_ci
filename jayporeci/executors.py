"""
A docker executor for Jaypore CI.
"""
import json
import subprocess
from enum import Enum
from copy import deepcopy
from typing import NamedTuple

import pendulum
from rich import print as rprint


from . import definitions as defs


def run(args, **kwargs):
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
    def parse(cls, kind) -> "NameKind":
        kind = {"net": NameKind.NET, "job": NameKind.JOB, "jci": NameKind.JCI}.get(kind)
        return kind


class Name(NamedTuple):
    """
    Name for things:

        - jayporeci__net__<sha>
        - jayporeci__jci__<sha>
        - jayporeci__job__<sha>__<jobname>
    """

    raw: str
    sha: str
    job: str = None
    kind: NameKind = None
    prefix: str = "jayporeci"
    sep: str = "__"

    @classmethod
    def parse(cls, name):
        if not name.startswith(f"{cls.prefix}{cls.sep}"):
            return None
        _, kind, *parts = name.split(cls.sep)
        kind = NameKind.parse(kind)
        if len(parts) == 1:
            return cls(name=name, sha=parts[0], kind=kind)
        if len(parts) == 2:
            return cls(name=name, sha=parts[0], job=parts[1], kind=kind)
        return None

    @classmethod
    def create(cls, *, kind: NameKind, sha: str, job: str = None) -> "Name":
        raw = None
        if kind == NameKind.NET:
            raw = cls.sep.join([cls.prefix, kind, sha])
        if kind == NameKind.JOB:
            raw = cls.sep.join([cls.prefix, kind, sha, job])
        if kind == NameKind.JCI:
            raw = cls.sep.join([cls.prefix, kind, sha])
        return Name(kind=kind, sha=sha, job=job, raw=raw)

    def get_related(self, kind: NameKind) -> str:
        return self.sep.join([self.prefix, kind, self.sha])


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

    def __init__(self, sha: str):
        super().__init__()
        self.sha = sha
        self.__execution_order__ = []

    def teardown(self):
        self.delete_run_network()
        self.delete_run_jobs()

    def setup(self):
        self.delete_old_containers()

    def delete_old_containers(self):
        too_old = pendulum.now().subtract(days=defs.const.retain_old_jobs_n_days)
        names_to_remove = set()
        for container in (
            run("docker ps -f status=exited --format json").stdout.decode().split()
        ):
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
            run(f"docker network ls {pipes} --format 'table {{.ID}}'")
            .stdout.decode()
            .split("\n")
        )[1:]
        net_ids = " ".join(net_ids)
        run(f"docker network rm {net_ids}")

    def create_network(self):
        """
        Will create a docker network.

        If it fails to do so in 3 attempts it will raise an
        exception and fail.
        """
        name = Name.create(kind=NameKind.NET, sha=self.sha)
        for _ in range(3):
            if (
                len(
                    run(f"docker network ls -f name={name.raw}")
                    .stdout.decode()
                    .split("\n")
                )
                != 1
            ):
                # self.logging().info("Found network", network_name=self.get_net())
                return
            run(f"docker network create -d bridge {name.raw}")
            # self.logging().info( "Create network",)
        raise Exception("Cannot create network")

    def delete_run_jobs(self):
        """
        Deletes all jobs associated with the pipeline for this
        executor.

        It will stop any jobs that are still running.
        """
        names_to_remove = set()
        for container in run("docker ps --format json").stdout.decode().split():
            container = json.loads(container)
            name = Name.parse(container["Names"])
            if name.sha == self.sha:
                names_to_remove.add(name)
        names = " ".join(name.raw for name in names_to_remove)
        run(f"docker stop -t 5 {names}")

    def delete_run_network(self):
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
        name = Name.create(kind=NameKind.JOB, sha=self.sha, job=job.name)
        cmd += [
            "--name",
            name.raw,
            "--network",
            name.get_related(NameKind.NET),
        ]
        if not job.is_service:
            cmd += ["--workdir", "/jayporeci/run"]
        cmd += [job.image, job.command if not job.is_service else None]
        rprint(cmd)
        container_id = run(cmd).stdout.decode().strip()
        self.__execution_order__.append((name.job, container_id, "Run"))
        return container_id

    def get_status(self, container_id: str) -> defs.JobState:
        """
        Given a run_id, it will get the status for that run.
        """
        inspect = run(f"docker inspect {container_id}").stdout.decode().strip()
        inspect = json.loads(inspect)
        status = defs.JobState(
            is_running=inspect["State"]["Status"] == "running",
            exit_code=int(inspect["State"]["ExitCode"]),
            logs="",
            started_at=pendulum.parse(inspect["State"]["StartedAt"]),
            finished_at=pendulum.parse(inspect["State"]["FinishedAt"])
            if inspect["State"]["FinishedAt"] != "0001-01-01T00:00:00Z"
            else None,
        )
        # --- logs
        logs = run(f"docker logs {container_id}").stdout.decode().strip()
        return status._replace(logs=logs)

    def get_execution_order(self):
        return {name: i for i, (name, *_) in enumerate(self.__execution_order__)}