import pendulum

from . import definitions as defs


class TextReporter(defs.Reporter):
    @classmethod
    def get_job_duration(cls, job: defs.Job) -> str:
        "Returns how long a job has been running"
        time = " --:--"
        if job.state is not None:
            if job.state.finished_at is not None and job.state.started_at is not None:
                s = job.state.finished_at - job.state.started_at
            elif job.state.started_at is not None:
                s = pendulum.now() - job.state.started_at
            else:
                s = None
            s = s.in_seconds() if s is not None else 0
            m = s // 60
            time = f"{m:>3}:{s % 60:>2}"
        return time

    def get_job_report(self, jobname: str) -> str:
        "If a job has reported some information, it will be reported here"
        return ""
        # with open(f"/jaypore_ci/run/{jobname}.txt", "r", encoding="utf-8") as fl:
        # return fl.read()

    def render(self, pipeline: defs.Pipeline, sha: str) -> str:
        """
        Returns a human readable report for a given pipeline.
        """
        max_name = max(len(job.name) for stage in pipeline.stages for job in stage.jobs)
        max_name = max(max_name, len(defs.const.jci))
        max_report = 10
        name = (defs.const.jci + " " * max_name)[:max_name]
        graph = [
            "",
            "```{defs.const.jci}",
            f"╔ {pipeline.get_status().get_dot()} : {name} [sha {sha[:10]}]",
        ]
        closer = "┗" + ("━" * (len(" O : ") + max_name + 1 + 1 + 8 + 1)) + "┛"
        for stage in pipeline.stages:
            nodes, edges = set(), set()
            for job in stage.jobs:
                # if job.stage != stage:
                # continue
                nodes.add(job.name)
                # edges |= {(p, job.name) for p in job.parents}
            if not nodes:
                continue
            graph += [f"┏━ {stage}", "┃"]
            for n in stage.jobs:
                name = (n.name + " " * max_name)[:max_name]
                status = n.state.status.get_dot()
                run_id = f"{n.state.run_id}"[:8] if n.state.run_id is not None else ""
                graph += [
                    f"┃ {status} : {name} [{run_id:<8}] {self.get_job_duration(n)}"
                ]
                try:
                    report = self.get_job_report(n.name)
                    report = " ".join(report.strip().split())
                    report = (report + " " * max_report)[:max_report]
                except FileNotFoundError:
                    report = " " * max_report
                graph[-1] += f" {report}"
                # if n.parents:
                # graph[-1] += f" ❮-- {n.parents}"
            graph += [closer]
        graph += ["```"]
        graph = "\n".join(graph)
        return f"\n{graph}"
