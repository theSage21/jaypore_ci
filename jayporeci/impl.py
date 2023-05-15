from typing import Dict, List, Union, Tuple, Any
from . import definitions as defs


class SimpleScheduler(defs.Scheduler):
    """
    The main scheduler for Jaypore CI.

    It will run stages in the sequence of their declaration.
    Within each stage it will run jobs in parallel unless they depend on
    something.
    """

    @classmethod
    def clean_name(cls, name: str) -> str:
        """
        Clean a given name so that it can be used inside of Jaypore CI.

        Currently this reduces names to their alphanumeric parts and turns
        everything else into a minus sign.
        """
        allowed_alphabet = "abcdefghijklmnopqrstuvwxyz1234567890"
        allowed_alphabet += allowed_alphabet.upper()
        return "".join(l if l in allowed_alphabet else "-" for l in name)

    def names_are_globally_unique(self) -> bool:
        """
        Make sure names are unique across stages / jobs.
        """
        seen = set()
        for stage in self.pipeline.stages or []:
            assert stage.name not in seen, f"Stage name taken: {stage.name}"
            seen.add(stage.name)
            for job in stage.jobs or set():
                assert job.name not in seen, f"Job name taken: {job.name}"
                seen.add(job.name)
        return True

    def stage(self, name: str, **kwargs: Dict[Any, Any]):
        """
        Create a :class:`~jayporeci.definitions.Stage` within which jobs can be
        defined.
        Any extra keyword arguments will be passed on to jobs inside this
        stage.
        """
        name = self.clean_name(name)
        stage = defs.Stage(name, tuple(kwargs.items()))
        stages = [] if self.pipeline.stages is None else list(self.pipeline.stages)
        self.pipeline = self.pipeline._replace(stages=tuple(list(stages) + [stage]))
        assert self.names_are_globally_unique()
        return stage

    def job(
        self,
        name: str,
        command: str,
        *,
        after: Union[List[str], str] = None,
        **kwargs: Dict[Any, Any],
    ):
        """
        Define a :class:`~jayporeci.definitions.Job` and link it with the jobs
        that it depends on.
        """
        name = self.clean_name(name)
        if self.pipeline.stages is None:
            self.stage("Jaypore CI")
        stages = self.pipeline.stages
        stage = stages[-1]
        # --- create job
        job = defs.Job(
            name,
            command,
            kwargs.pop("is_service", False),
            kwargs.pop("state", defs.Status.PENDING),
            kwargs.pop("image", None),
            tuple(kwargs.items()),
        )
        if stage.jobs is None:
            stage = stage._replace(jobs=tuple([job]))
        else:
            stage = stage._replace(jobs=tuple(list(stage.jobs) + [job]))
        # --- assign edges in stage
        if after is not None:
            if isinstance(after, str):
                after = [after]
            after = [self.clean_name(dep_name) for dep_name in after]
            for dep_name in after:
                assert stage.has_job(
                    dep_name
                ), f"Dependency not found: {dep_name}: {stage}"
            for dep_name in after:
                stage = stage.add_edge(
                    frm_name=dep_name, to_name=job.name, kind=defs.EdgeKind.ALL_SUCCESS
                )
        # --- assign in right location
        stages = list(stages[:-1]) + [stage]
        self.pipeline = self.pipeline._replace(stages=tuple(stages))
        assert self.names_are_globally_unique()


class DockerExecutor(defs.Executor):
    pass


class CliPlatform(defs.Platform):
    pass


class TextReporter(defs.Reporter):
    pass


class GitRepo(defs.Repo):
    @classmethod
    def from_env(cls) -> "GitRepo":
        return cls("", "", "", "")
