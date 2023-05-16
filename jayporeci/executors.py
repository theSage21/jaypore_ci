"""
A docker executor for Jaypore CI.
"""
import json
import subprocess
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


class Names(NamedTuple):
    """
    Names for things:

        - jayporeci__net__<sha>
        - jayporeci__jci__<sha>
        - jayporeci__job__<sha>__<jobname>
    """

    name: str
    sha: str
    job: str = None
    kind: str = None
    prefix: str = "jayporeci"
    sep: str = "__"

    @classmethod
    def parse(cls, name):
        if not name.startswith(f"{cls.prefix}{cls.sep}"):
            return None
        _, kind, *parts = name.split(cls.sep)
        if len(parts) == 1:
            return cls(name=name, sha=parts[0])
        if len(parts) == 2:
            return cls(name=name, sha=parts[0], job=parts[1])
        return None

    def get_related(self, kind):
        return self.sep.join([self.prefix, kind, self.sha])


class DockerExecutor(defs.Executor):
    """
    Run jobs via docker.

    Using this executor will:
        - Create a separate network for each run
        - Run jobs as part of the network
        - Clean up all jobs when the pipeline exits.
    """

    def __init__(self):
        super().__init__()
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
            name = Names.parse(container["Names"])
            if name is None:
                continue
            finished_at = pendulum.parse(container["CreatedAt"])
            if finished_at <= too_old:
                names_to_remove.add(name)
        spaced_names = " ".join(cname.name for cname in names_to_remove)
        run(f"docker container rm -v {spaced_names}")
        # Remove networks
        net_ids = [
            cname.sep.join([cname.prefix, cname.sha]) for cname in names_to_remove
        ]
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
        assert self.pipe_id is not None, "Cannot create network if pipe is not set"
        for _ in range(3):
            if (
                len(
                    run(f"docker network ls -f name={self.get_net()}")
                    .stdout.decode()
                    .split("\n")
                )
                != 1
            ):
                self.logging().info("Found network", network_name=self.get_net())
                return
            self.logging().info(
                "Create network",
                subprocess=run(f"docker network create -d bridge {self.get_net()}"),
            )
        raise TriggerFailed("Cannot create network")

    def delete_all_jobs(self):
        """
        Deletes all jobs associated with the pipeline for this
        executor.

        It will stop any jobs that are still running.
        """
        assert self.pipe_id is not None, "Cannot delete jobs if pipe is not set"
        job = None
        for job in self.pipeline.jobs.values():
            if job.run_id is not None and not job.run_id.startswith("pyrun_"):
                container = self.docker.containers.get(job.run_id)
                container.stop(timeout=1)
                self.logging().info("Stop job:", run_id=job.run_id)
                job.check_job(with_update_report=False)
        if job is not None:
            job.check_job()
        self.logging().info("All jobs stopped")

    def delete_network(self):
        """
        Delete the network for this executor.
        """
        assert self.pipe_id is not None, "Cannot delete network if pipe is not set"
        try:
            net = self.docker.networks.get(self.get_net())
            net.remove()
        except docker.errors.NotFound:
            self.logging().error("Delete network: Not found", netid=self.get_net())

    def get_job_name(self, job, tail=False):
        """
        Generates a clean job name slug.
        """
        name = clean.name(job.name)
        if tail:
            return name
        return f"jayporeci__job__{self.pipe_id}__{name}"

    def run(self, job: "Job") -> str:
        """
        Run the given job and return a docker container ID.
        In case something goes wrong it will raise TriggerFailed
        """
        assert self.pipe_id is not None, "Cannot run job if pipe id is not set"
        ex_kwargs = deepcopy(job.executor_kwargs)
        env = job.get_env()
        env.update(ex_kwargs.pop("environment", {}))
        env["REPO_SHA"] = const.repo_sha
        env["REPO_ROOT"] = const.repo_root
        env["ENV"] = const.env
        trigger = {
            "detach": True,
            "environment": env,
            "volumes": list(
                set(
                    [
                        "/var/run/docker.sock:/var/run/docker.sock",
                        "/usr/bin/docker:/usr/bin/docker:ro",
                        f"/tmp/jayporeci__src__{self.pipeline.remote.sha}:/jaypore_ci/run",
                    ]
                    + (ex_kwargs.pop("volumes", []))
                )
            ),
            "name": self.get_job_name(job),
            "network": self.get_net(),
            "image": job.image,
            "command": job.command if not job.is_service else None,
        }
        for key, value in ex_kwargs.items():
            if key in trigger:
                self.logging().warning(
                    f"Overwriting existing value of `{key}` for job trigger.",
                    old_value=trigger[key],
                    new_value=value,
                )
            trigger[key] = value
        if not job.is_service:
            trigger["working_dir"] = "/jaypore_ci/run"
        if not job.is_service:
            assert job.command
        rprint(trigger)
        try:
            container = self.docker.containers.run(**trigger)
            self.__execution_order__.append(
                (self.get_job_name(job, tail=True), container.id, "Run")
            )
            return container.id
        except docker.errors.APIError as e:
            self.logging().exception(e)
            raise TriggerFailed(e) from e

    def get_status(self, run_id: str) -> JobStatus:
        """
        Given a run_id, it will get the status for that run.
        """
        inspect = self.client.inspect_container(run_id)
        status = JobStatus(
            is_running=inspect["State"]["Running"],
            exit_code=int(inspect["State"]["ExitCode"]),
            logs="",
            started_at=pendulum.parse(inspect["State"]["StartedAt"]),
            finished_at=pendulum.parse(inspect["State"]["FinishedAt"])
            if inspect["State"]["FinishedAt"] != "0001-01-01T00:00:00Z"
            else None,
        )
        # --- logs
        self.logging().debug("Check status", status=status)
        logs = self.docker.containers.get(run_id).logs().decode()
        return status._replace(logs=logs)

    def get_execution_order(self):
        return {name: i for i, (name, *_) in enumerate(self.__execution_order__)}
