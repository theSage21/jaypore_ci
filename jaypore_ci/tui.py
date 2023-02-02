import subprocess
from copy import deepcopy

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

                                 :J55555557.      
                                 :P#######?       
                                 :5#BBBBB#?       
                                 :5#BBBBB#?       
                                 :5#BBBBB#?       
              .~^                :5#BBBBB#?       
            ^JG#G!               :5#BBBBB#?       
          :JB##B#B?.             :5#BBBBB#?       
         ~G##BBBB##J:            :5#BBBBB#?       
        ~G#BBBBB#G?^.            :5#BBBBB#?       
       :P#BBBBB#P^               :5#BBBBB#?       
       !B#BBBB#G~                :P#######?       
       7#BBBBB#P:                .~!!!!!!!^       
       !B#BBBB#G~                                 
       :P#BBBBB#P~                                
        ~G#BBBBB#BJ^.                             
         ~P##BBBB##BPY?!!!!?YJ.                   
          :JB###BBB###########5:                  
            ^?PB####BBBBBBBBBB#G!                 
              .~?5GB##########BGY^                
                  .^~!7????7!~^.                  
"""


def get_logs(cid):
    return subprocess.check_output(
        f"docker logs {cid}",
        shell=True,
        stderr=subprocess.STDOUT,
    ).decode()


def get_status(sha):
    with open(
        f"/tmp/jayporeci__src__{sha}/jaypore_ci.status.txt", "r", encoding="utf-8"
    ) as fl:
        status = fl.read()
        status = status.replace("```jayporeci", "").replace("```", "")
    return status


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
    DEFAULT_PIPE = {
        "sha": None,
        "jobs": [],
        "cid": None,
        "completed": True,
        "kind": "pipe",
    }
    for line in lines:
        if PREFIX not in line:
            continue
        kind, *details = line.split(PREFIX)[1].split("__")
        cid = line.split(" ")[0]
        if kind == "pipe":
            if cid not in pipes:
                pipes[cid] = deepcopy(DEFAULT_PIPE)
            if pipes[cid]["sha"] is None:
                pipes[cid]["sha"] = details[0]
            if pipes[cid]["cid"] is None:
                pipes[cid]["cid"] = cid
            pipes[cid]["completed"] = "Exited (" in line
        elif kind == "job":
            pipe_cid, name = details
            pipe_cid = pipe_cid[:12]
            if pipe_cid not in pipes:
                pipes[pipe_cid] = deepcopy(DEFAULT_PIPE)
            pipes[pipe_cid]["jobs"].append(
                {
                    "cid": cid[:12],
                    "name": name,
                    "completed": "Exited (" in line,
                    "kind": "job",
                }
            )
    return {cid: pipe for cid, pipe in pipes.items() if pipe["sha"] is not None}


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
            s = " " if pipe["completed"] else "*"
            pipe_node = tree.root.add(
                f"{s} {pipe['sha'][:8]}", data=pipe, expand=not pipe["completed"]
            )
            pipe_node.add_leaf(
                f"{s} {pipe['cid'][:4]}: JayporeCI",
                data={
                    "cid": pipe["cid"],
                    "sha": pipe["sha"],
                    "name": "Status",
                    "kind": "status",
                    "completed": pipe["completed"],
                },
            )
            for job in pipe["jobs"]:
                s = " " if job["completed"] else "*"
                pipe_node.add_leaf(f"{s} {job['cid'][:4]}: {job['name']}", data=job)
        # ---
        yield Container(
            tree,
            Vertical(Static(id="code", expand=True, markup=False), id="code-view"),
        )
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:  # pylint: disable=unused-argument
        self.query_one(Tree).show_root = False
        self.query_one(Tree).focus()
        code_view = self.query_one("#code", Static)
        code_view.update(HELP)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when the user click a node in the job tree."""
        event.stop()
        code_view = self.query_one("#code", Static)
        data = event.node.data
        cid = None
        if isinstance(data, dict) and "cid" in data and data.get("kind") == "pipe":
            cid = name = data["cid"]
            name = f"Pipeline for SHA: {data['sha']}"
        elif isinstance(data, dict) and "sha" in data and data.get("kind") == "status":
            name = f"Status: {data['sha']}"
            try:
                code_view.update(get_status(data["sha"]))
            except Exception:  # pylint: disable=broad-except
                code_view.update(Traceback(theme="github-dark", width=None))
                self.sub_title = "ERROR"
            return
        elif isinstance(data, dict) and "cid" in data and data.get("kind") == "job":
            cid = name = data["cid"]
            name = f"Job: {data['name']}"
        if cid is None:
            code_view.update(HELP)
            return
        try:
            logs = get_logs(cid)
        except Exception:  # pylint: disable=broad-except
            code_view.update(Traceback(theme="github-dark", width=None))
            self.sub_title = "ERROR"
        else:
            code_view.update(logs)
            self.sub_title = name
