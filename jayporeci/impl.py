from . import definitions as defs


class SimpleScheduler(defs.Scheduler):
    @classmethod
    def clean_name(cls, name: str) -> str:
        """
        Clean a given name so that it can be used inside of Jaypore CI.

        Currently this reduces names to their alphanumeric parts and turns
        everything else into a minus sign.
        """
        allowed_alphabet = "abcdefghijklmnopqrstuvwxyz1234567890"
        allowed_alphabet += allowed_alphabet.upper()
        return "".join(l if l in allowed_alphabet else "-" for l in given)

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

    def stage(self, name: str, **kwargs: Dict[Any, Any]):
        """
        Create a stage for the pipelines.
        """
        name = self.clean_name(name)
        stage = defs.Stage(name, kwargs)
        stages = [] if self.pipeline.stages is None else list(self.pipeline.stages)
        self.pipeline = self.pipeline._replace(stages=tuple(list(stages) + [stage]))
        assert self.names_are_globally_unique()

    def job(
        self,
        name: str,
        command: str,
        *,
        after: List[str] = None,
        **kwargs: Dict[Any, Any],
    ):
        name = self.clean_name(name)
        if self.pipeline.stages is None:
            self.stage("Jaypore CI")
        stages = self.pipeline.stages
        stage = stages[-1]
        # --- create job
        job = defs.Job(name, command, kwargs=kwargs)
        # --- assign in right location
        if stage.jobs is None:
            stage = stage._replace(jobs={job})
        stages = list(stages[:-1]) + [stage]
        self.pipeline._replace(stages=tuple(stages))
        assert self.names_are_globally_unique(name)
