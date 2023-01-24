import pendulum
from jaypore_ci.interfaces import Reporter, Status


def __get_time_format__(job):
    time = " --:--"
    if job.run_state is not None:
        if (
            job.run_state.finished_at is not None
            and job.run_state.started_at is not None
        ):
            s = job.run_state.finished_at - job.run_state.started_at
        elif job.run_state.started_at is not None:
            s = pendulum.now() - job.run_state.started_at
        else:
            s = None
        s = s.in_seconds() if s is not None else 0
        m = s // 60
        time = f"{m:>3}:{s % 60:>2}"
    return time


__ST_MAP__ = {
    Status.RUNNING: "🔵",
    Status.FAILED: "🔴",
    Status.PASSED: "🟢",
}


class Text(Reporter):
    def render(self, pipeline):
        """
        Returns a human readable report for a given pipeline.
        """
        max_name = max(len(job.name) for job in pipeline.jobs.values())
        max_name = max(max_name, len("jayporeci"))
        name = ("JayporeCI" + " " * max_name)[:max_name]
        graph = [
            "",
            "```jayporeci",
            f"╔ {pipeline.get_status_dot()} : {name} [sha {pipeline.remote.sha[:10]}]",
        ]
        closer = "┗" + ("━" * (len(" O : ") + max_name + 1 + 1 + 8 + 1)) + "┛"
        for stage in pipeline.stages:
            nodes, edges = set(), set()
            for job in pipeline.jobs.values():
                if job.stage != stage:
                    continue
                nodes.add(job.name)
                edges |= {(p, job.name) for p in job.parents}
            if not nodes:
                continue
            graph += [f"┏━ {stage}", "┃"]
            for n in sorted(
                nodes, key=lambda x: (len(pipeline.jobs[x].parents), x)
            ):  # Fewer parents first
                n = pipeline.jobs[n]
                name = (n.name + " " * max_name)[:max_name]
                status = __ST_MAP__.get(n.status, "🟡")
                run_id = f"{n.run_id}"[:8] if n.run_id is not None else ""
                graph += [f"┃ {status} : {name} [{run_id:<8}] {__get_time_format__(n)}"]
                if n.parents:
                    graph[-1] += f" ❮-- {n.parents}"
            graph += [closer]
        graph += ["```"]
        graph = "\n".join(graph)
        return f"\n{graph}"
