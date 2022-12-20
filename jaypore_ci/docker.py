import subprocess

from rich import print as rprint

from jaypore_ci.interfaces import Executor
from jaypore_ci.logging import logger


class Docker(Executor):
    """
    Run docker jobs
    """

    def check_output(self, cmd):
        return (
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            .decode()
            .strip()
        )

    def __init__(self):
        super().__init__()
        self.pipe_id = None
        self.pipeline = None

    def logging(self):
        return logger.bind(pipe_id=self.pipe_id, network_name=self.get_net())

    def set_pipeline(self, pipeline):
        if self.pipe_id is not None:
            self.delete_network()
            self.delete_all_jobs()
        self.pipe_id = id(pipeline)
        self.pipeline = pipeline
        self.create_network()

    def __exit__(self, exc_type, exc_value, traceback):
        self.delete_network()
        self.delete_all_jobs()

    def get_net(self):
        return f"jaypore_{self.pipe_id}" if self.pipe_id is not None else None

    def create_network(self):
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
                subprocess=self.check_output(
                    f"docker network create -d bridge {self.get_net()}"
                ),
            )
        raise Exception("Cannot create network")

    def delete_all_jobs(self):
        assert self.pipe_id is not None, "Cannot delete jobs if pipe is not set"
        job = None
        for job in self.pipeline.jobs.values():
            if job.run_id is not None and not job.run_id.startswith("pyrun_"):
                self.logging().info(
                    "Stop job:",
                    subprocess=self.check_output(f"docker stop -t 1 {job.run_id}"),
                )
                job.check_job(with_update_report=False)
        if job is not None:
            job.check_job()
        self.logging().info("All jobs stopped")

    def delete_network(self):
        assert self.pipe_id is not None, "Cannot delete network if pipe is not set"
        self.logging().info(
            "Delete network",
            subprocess=self.check_output(
                f"docker network rm {self.get_net()} || echo 'No such net'"
            ),
        )

    def get_job_name(self, job):
        name = "".join(
            l
            for l in job.name.lower().replace(" ", "_")
            if l in "abcdefghijklmnopqrstuvwxyz_"
        )
        return f"{self.get_net()}_{name}"

    def run(self, job: "Job") -> str:
        assert self.pipe_id is not None, "Cannot run job if pipe id is not set"
        self.pipe_id = id(job.pipeline) if self.pipe_id is None else self.pipe_id
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
        return self.check_output(" ".join(t for t in trigger if t is not None))

    def get_status(self, run_id: str) -> (str, str):
        ps_out = self.check_output(f"docker ps -f 'id={run_id}' --no-trunc")
        is_running = run_id in ps_out
        # --- exit code
        exit_code = self.check_output(
            f"docker inspect {run_id}" " --format='{{.State.ExitCode}}'"
        )
        exit_code = int(exit_code)
        # --- logs
        logs = self.check_output(f"docker logs {run_id}")
        self.logging().debug(
            "Check status",
            run_id=run_id,
            is_running=is_running,
            exit_code=exit_code,
        )
        return is_running, exit_code, logs
