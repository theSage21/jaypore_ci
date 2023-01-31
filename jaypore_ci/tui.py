import subprocess

from rich.traceback import Traceback

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Tree, Footer, Header, Static

HELP = """
- The tree shows commit SHA values for pipelines that have run on this machine.
- Clicking on the SHA will:
    - Toggle the list of jobs for that pipeline.
    - Show pipeline logs
- Clicking on the job will show logs for that job
"""


def get_pipes_from_docker_ps():
    lines = (
        subprocess.check_output(
            "docker ps -a",
            shell=True,
            stderr=subprocess.STDOUT,
        )
        .decode()
        .split("\n")
    )

    pipes = {}
    PREFIX = "jayporeci__"
    for line in lines:
        if PREFIX not in line:
            continue
        kind, *details = line.split(PREFIX)[1].split("__")
        cid = line.split(" ")[0]
        if kind == "pipe":
            if cid not in pipes:
                pipes[cid] = {"sha": None, "jobs": [], "cid": None}
            if pipes[cid]["sha"] is None:
                pipes[cid]["sha"] = details[0][:8]
            if pipes[cid]["cid"] is None:
                pipes[cid]["cid"] = cid
        elif kind == "job":
            pipe_cid, name = details
            pipe_cid = pipe_cid[:12]
            if pipe_cid not in pipes:
                pipes[pipe_cid] = {"sha": None, "jobs": [], "cid": None}
            pipes[pipe_cid]["jobs"].append((cid[:12], name))
    return pipes


class Console(App):
    """Textual CI Job browser app."""

    CSS_PATH = "tui.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header()
        # Find the job tree
        tree: Tree[dict] = Tree("JayporeCI", id="tree-view")
        tree.root.expand()
        pipes = get_pipes_from_docker_ps()
        for pipe in pipes.values():
            pipe_node = tree.root.add(pipe["sha"], data=pipe)
            for job in pipe["jobs"]:
                job_cid, job_name = job
                pipe_node.add_leaf(f"{job_cid[:4]}: {job_name}", data=job)
        # ---
        yield Container(
            tree,
            Vertical(Static(id="code", expand=True, markup=False), id="code-view"),
        )
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:  # pylint: disable=unused-argument
        self.query_one(Tree).show_root = False
        self.query_one(Tree).focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when the user click a node in the job tree."""
        event.stop()
        code_view = self.query_one("#code", Static)
        data = event.node.data
        cid = None
        if isinstance(data, dict) and "cid" in data:
            cid = name = data["cid"]
            name = f"Pipeline for SHA: {data['sha']}"
        elif isinstance(data, tuple):
            cid, name = data
            name = f"Job: {name}"
        if cid is None:
            code_view.update(HELP)
            return
        try:
            logs = subprocess.check_output(
                f"docker logs {cid}",
                shell=True,
                stderr=subprocess.STDOUT,
            ).decode()
        except Exception:  # pylint: disable=broad-except
            code_view.update(Traceback(theme="github-dark", width=None))
            self.sub_title = "ERROR"
        else:
            code_view.update(logs)
            self.sub_title = name
