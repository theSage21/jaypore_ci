"""
A docker executor for Jaypore CI.
"""
from copy import deepcopy

import pendulum
import docker
from rich import print as rprint
from tqdm import tqdm

from jaypore_ci import clean
from jaypore_ci.interfaces import Executor, TriggerFailed, JobStatus
from jaypore_ci.logging import logger


class Docker(Executor):
    """
    Run jobs via docker. To communicate with docker we use the `Python docker
    sdk <https://docker-py.readthedocs.io/en/stable/client.html>`_.

    Using this executor will:
        - Create a separate network for each run
        - Run jobs as part of the network
        - Clean up all jobs when the pipeline exits.
    """

    def __init__(self):
        super().__init__()
        self.pipe_id = None
        self.pipeline = None
        self.docker = docker.from_env()
        self.client = docker.APIClient()
        self.__execution_order__ = []

    def logging(self):
        """
        Returns a logging instance that has executor specific
        information bound to it.
        """
        return logger.bind(pipe_id=self.pipe_id, network_name=self.get_net())

    def set_pipeline(self, pipeline):
        """
        Set executor's pipeline to the given one.

        This will clean up old networks and create new ones.
        """
        if self.pipe_id is not None:
            self.delete_network()
            self.delete_all_jobs()
        self.pipe_id = pipeline.pipe_id
        self.pipeline = pipeline
        self.create_network()

    def teardown(self):
        self.delete_network()
        self.delete_all_jobs()

    def setup(self):
        self.delete_old_containers()

    def delete_old_containers(self):
        a_week_back = pendulum.now().subtract(days=7)
        for container in tqdm(
            self.docker.containers.list(filters={"status": "exited"}),
            desc="Removing jobs older than a week",
        ):
            if "jayporeci_" not in container.name:
                continue
            finished_at = pendulum.parse(container.attrs["State"]["FinishedAt"])
            if finished_at <= a_week_back:
                container.remove(v=True)

    def get_net(self):
        """
        Return a network name based on what the curent pipeline is.
        """
        return f"jayporeci__net__{self.pipe_id}" if self.pipe_id is not None else None

    def create_network(self):
        """
        Will create a docker network.

        If it fails to do so in 3 attempts it will raise an
        exception and fail.
        """
        assert self.pipe_id is not None, "Cannot create network if pipe is not set"
        for _ in range(3):
            if len(self.docker.networks.list(names=[self.get_net()])) != 0:
                self.logging().info("Found network", network_name=self.get_net())
                return
            self.logging().info(
                "Create network",
                subprocess=self.docker.networks.create(
                    name=self.get_net(), driver="bridge"
                ),
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
        trigger = {
            "detach": True,
            "environment": env,
            "volumes": list(
                set(
                    [
                        "/var/run/docker.sock:/var/run/docker.sock",
                        "/usr/bin/docker:/usr/bin/docker:ro",
                        "/tmp/jayporeci__cidfiles:/jaypore_ci/cidfiles:ro",
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
