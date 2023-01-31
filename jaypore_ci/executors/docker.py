"""
A docker executor for Jaypore CI.
"""
import json
import subprocess

import pendulum
from rich import print as rprint

from jaypore_ci.interfaces import Executor, TriggerFailed, JobStatus
from jaypore_ci.logging import logger


def __check_output__(cmd):
    """
    Common arguments that need to be provided while
    calling subprocess.check_output
    """
    return (
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        .decode()
        .strip()
    )


class Docker(Executor):
    """
    Run jobs via docker.

    This will:
        - Create a separate network for each run
        - Run jobs as part of the network
        - Clean up all jobs when the pipeline exits.
    """

    def __init__(self):
        super().__init__()
        self.pipe_id = None
        self.pipeline = None

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
        self.pipe_id = __check_output__(
            "cat /proc/self/cgroup | grep name= | awk -F/ '{print $3}'"
        )
        self.pipeline = pipeline
        self.create_network()

    def __exit__(self, exc_type, exc_value, traceback):
        self.delete_network()
        self.delete_all_jobs()

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
            net_ls = subprocess.run(
                f"docker network ls | grep {self.get_net()}",
                shell=True,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if net_ls.returncode == 0:
                self.logging().info(
                    "Found network", network_name=self.get_net(), subprocess=net_ls
                )
                return net_ls
            self.logging().info(
                "Create network",
                subprocess=__check_output__(
                    f"docker network create -d bridge {self.get_net()}"
                ),
            )
        raise Exception("Cannot create network")

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
                self.logging().info(
                    "Stop job:",
                    subprocess=__check_output__(f"docker stop -t 1 {job.run_id}"),
                )
                job.check_job(with_update_report=False)
        if job is not None:
            job.check_job()
        self.logging().info("All jobs stopped")

    def delete_network(self):
        """
        Delete the network for this executor.
        """
        assert self.pipe_id is not None, "Cannot delete network if pipe is not set"
        self.logging().info(
            "Delete network",
            subprocess=__check_output__(
                f"docker network rm {self.get_net()} || echo 'No such net'"
            ),
        )

    def get_job_name(self, job):
        """
        Generates a clean job name slug.
        """
        name = "".join(
            l
            for l in job.name.lower().replace(" ", "_")
            if l in "abcdefghijklmnopqrstuvwxyz_1234567890"
        )
        return f"jayporeci__job__{self.pipe_id}__{name}"

    def run(self, job: "Job") -> str:
        """
        Run the given job and return a docker container ID.
        In case something goes wrong it will raise TriggerFailed
        """
        assert self.pipe_id is not None, "Cannot run job if pipe id is not set"
        env_vars = [f"--env {key}={val}" for key, val in job.get_env().items()]
        trigger = [
            "docker run -d",
            "-v /var/run/docker.sock:/var/run/docker.sock",
            f"-v /tmp/jaypore_{job.pipeline.remote.sha}:/jaypore_ci/run",
            *["--workdir /jaypore_ci/run" if not job.is_service else None],
            f"--name {self.get_job_name(job)}",
            f"--network {self.get_net()}",
            *env_vars,
            job.image,
            job.command if not job.is_service else None,
        ]
        if not job.is_service:
            assert job.command
        rprint(trigger)
        trigger = " ".join(t for t in trigger if t is not None)
        run_job = subprocess.run(
            trigger,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if run_job.returncode == 0:
            return run_job.stdout.decode().strip()
        raise TriggerFailed(run_job)

    def get_status(self, run_id: str) -> JobStatus:
        """
        Given a run_id, it will get the status for that run.
        """
        inspect = json.loads(__check_output__(f"docker inspect {run_id}"))[0]
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
        logs = __check_output__(f"docker logs {run_id}")
        return status._replace(logs=logs)
