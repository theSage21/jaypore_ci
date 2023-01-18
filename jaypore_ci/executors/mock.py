"""
A mock executor that actually does not run anything.
"""
import uuid

from jaypore_ci.interfaces import Executor, JobStatus
from jaypore_ci.logging import logger


class Mock(Executor):
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
        self.__log__ = []
        self.__status__ = {}

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
        self.pipe_id = id(pipeline)
        self.pipeline = pipeline
        self.create_network()

    def __exit__(self, exc_type, exc_value, traceback):
        self.delete_network()
        self.delete_all_jobs()

    def get_net(self):
        """
        Return a network name based on what the curent pipeline is.
        """
        return f"jaypore_{self.pipe_id}" if self.pipe_id is not None else None

    def create_network(self):
        """
        Will create a docker network.

        If it fails to do so in 3 attempts it will raise an
        exception and fail.
        """
        assert self.pipe_id is not None, "Cannot create network if pipe is not set"
        return self.get_net()

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
        self.logging().info("Delete network", net=self.get_net())

    def get_job_name(self, job):
        """
        Generates a clean job name slug.
        """
        name = "".join(
            l
            for l in job.name.lower().replace(" ", "_")
            if l in "abcdefghijklmnopqrstuvwxyz_1234567890"
        )
        return name

    def run(self, job: "Job") -> str:
        """
        Run the given job and return a docker container ID.
        """
        assert self.pipe_id is not None, "Cannot run job if pipe id is not set"
        self.pipe_id = id(job.pipeline) if self.pipe_id is None else self.pipe_id
        if not job.is_service:
            assert job.command
        name = self.get_job_name(job)
        if name in self.__status__:
            return None
        run_id = uuid.uuid4().hex
        self.__log__.append((name, run_id, "Run"))
        self.__status__[name] = self.__status__[run_id] = True
        self.logging().info(
            "Run job",
            run_id=run_id,
            env_vars=job.get_env(),
            is_service=job.is_service,
            name=self.get_job_name(job),
            net=self.get_net(),
            image=job.image,
            command=job.command if not job.is_service else None,
        )
        return run_id

    def get_status(self, run_id: str) -> JobStatus:
        """
        Given a run_id, it will get the status for that run.
        """
        status = JobStatus(True, None, "", None, None)
        if run_id in self.__status__:
            status = JobStatus(False, 0, "fake logs", None, None)
        return status

    def get_execution_order(self):
        return {name: i for i, (name, *log) in enumerate(self.__log__)}
