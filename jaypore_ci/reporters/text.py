from jaypore_ci.interfaces import Reporter, Status


class Text(Reporter):
    def render(self, pipeline):
        """
        Returns a human readable report for a given pipeline.
        """
        st_map = {
            Status.RUNNING: "🔵",
            Status.FAILED: "🔴",
            Status.PASSED: "🟢",
        }
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
                nodes, key=lambda x: len(pipeline.jobs[x].parents)
            ):  # Fewer parents first
                n = pipeline.jobs[n]
                name = (n.name + " " * max_name)[:max_name]
                status = st_map.get(n.status, "🟡")
                run_id = f"{n.run_id}"[:8] if n.run_id is not None else ""
                if n.parents:
                    graph += [f"┃ {status} : {name} [{run_id:<8}] ❮-- {n.parents}"]
                else:
                    graph += [f"┃ {status} : {name} [{run_id:<8}]"]
            graph += [closer]
        graph += ["```"]
        graph = "\n".join(graph)
        return f"\n{graph}"
