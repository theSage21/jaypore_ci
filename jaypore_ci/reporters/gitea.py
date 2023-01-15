import re
from collections import namedtuple
from jaypore_ci.interfaces import Reporter, Status
from jaypore_ci.logging import jaypore_logs


def __node_mod__(nodes):
    mod = 1
    if len(nodes) > 5:
        mod = 2
    if len(nodes) > 10:
        mod = 3
    return mod


ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_logs(logs):
    """
    Clean logs so that they don't have HTML/ANSI color codes in them.
    """
    for old, new in [("<", r"\<"), (">", r"\>"), ("`", '"'), ("\r", "\n")]:
        logs = logs.replace(old, new)
    return [line.strip() for line in ansi_escape.sub("", logs).split("\n")]


class Gitea(Reporter):
    def render(self, pipeline):
        """
        Returns a markdown report for a given pipeline.

        It will include a mermaid graph and a collapsible list of logs for each
        job.
        """
        return f"""
<details>
    <summary>JayporeCi: {pipeline.get_status_dot()} {pipeline.remote.sha[:10]}</summary>

{self.__render_graph__(pipeline)}
{self.__render_logs__(pipeline)}

</details>"""

    def __render_graph__(self, pipeline) -> str:  # pylint: disable=too-many-locals
        """
        Render a mermaid graph given the jobs in the pipeline.
        """
        st_map = {
            Status.PENDING: "pending",
            Status.RUNNING: "running",
            Status.FAILED: "failed",
            Status.PASSED: "passed",
            Status.TIMEOUT: "timeout",
            Status.SKIPPED: "skipped",
        }
        mermaid = f"""
```mermaid
flowchart {pipeline.graph_direction}
"""
        for stage in pipeline.stages:
            nodes, edges = set(), set()
            for job in pipeline.jobs.values():
                if job.stage != stage:
                    continue
                nodes.add(job.name)
                edges |= {(p, job.name) for p in job.parents}
            mermaid += f"""
            subgraph {stage}
                direction {pipeline.graph_direction}
            """
            ref = {n: f"{stage}_{i}" for i, n in enumerate(nodes)}
            # If there are too many nodes, scatter them with different length arrows
            mod = __node_mod__([n for n in nodes if not pipeline.jobs[n].parents])
            for i, n in enumerate(nodes):
                n = pipeline.jobs[n]
                if n.parents:
                    continue
                arrow = "." * ((i % mod) + 1)
                arrow = f"-{arrow}->"
                mermaid += f"""
                s_{stage}(( )) {arrow} {ref[n.name]}({n.name}):::{st_map[n.status]}"""
            mod = __node_mod__([n for n in nodes if pipeline.jobs[n].parents])
            for i, (a, b) in enumerate(edges):
                a, b = pipeline.jobs[a], pipeline.jobs[b]
                arrow = "." * ((i % mod) + 1)
                arrow = f"-{arrow}->"
                mermaid += f"""
                {ref[a.name]}({a.name}):::{st_map[a.status]} {arrow} {ref[b.name]}({b.name}):::{st_map[b.status]}"""
            mermaid += """
            end
            """
        for s1, s2 in zip(pipeline.stages, pipeline.stages[1:]):
            mermaid += f"""
            {s1} ---> {s2}
            """
        mermaid += """

            classDef pending fill:#aaa, color:black, stroke:black,stroke-width:2px,stroke-dasharray: 5 5;
            classDef skipped fill:#aaa, color:black, stroke:black,stroke-width:2px;
            classDef assigned fill:#ddd, color:black, stroke:black,stroke-width:2px;
            classDef running fill:#bae1ff,color:black,stroke:black,stroke-width:2px,stroke-dasharray: 5 5;
            classDef passed fill:#88d8b0, color:black, stroke:black;
            classDef failed fill:#ff6f69, color:black, stroke:black;
            classDef timeout fill:#ffda9e, color:black, stroke:black;
``` """
        return mermaid

    def __render_logs__(self, pipeline):
        """
        Collect all pipeline logs and render into a single collapsible text.
        """
        all_logs = []
        fake_job = namedtuple("fake_job", "name logs")(
            "JayporeCi",
            {"stdout": clean_logs("\n".join(jaypore_logs))},
        )
        for job in [fake_job] + list(pipeline.jobs.values()):
            job_log = []
            for logname, stream in job.logs.items():
                job_log += [f"============== {logname} ============="]
                job_log += [line.strip() for line in stream]
            if job_log:
                all_logs += [
                    "- <details>",
                    f"    <summary>Logs: {job.name}</summary>",
                    "",
                    "    ```",
                    *[f"    {line}" for line in job_log],
                    "    ```",
                    "",
                    "  </details>",
                ]
        return "\n".join(all_logs)
