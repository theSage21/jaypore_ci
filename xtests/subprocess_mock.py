import random
import subprocess
from typing import NamedTuple


class ProcMock(NamedTuple):
    returncode: int
    stdout: str


def sha():
    return hex(random.getrandbits(128))


__rev_parse__ = sha()
__hash_object__ = sha()
__mktree = sha()
__commit_tree = sha()
__update_ref__ = sha()


def check_output(cmd, **_):
    text = ""
    # repos.git
    if "git diff" in cmd:
        text = "some\nfiles\nthat\nwere\nchanged"
    elif "git remote -v" in cmd and "grep https" in cmd:
        text = "https://fake_remote.subprocessmock.com/fake_owner/fake_repo.git"
    elif "git branch" in cmd and "grep" in cmd:
        text = "subprocess_mock_fake_branch"
    elif "rev-parse HEAD" in cmd:
        text = __rev_parse__
    elif "git log -1" in cmd:
        text = "some_fake_git_commit_message\nfrom_subprocess_mock"
    # jci
    elif "cat /proc/self/cgroup" in cmd:
        text = "fake_pipe_id_from_subprocess_mock"
    # remotes.git
    elif "git hash-object" in cmd:
        text = __hash_object__
    elif "git mktree" in cmd:
        text = __mktree
    elif "git commit-tree" in cmd:
        text = __commit_tree
    elif "git update-ref" in cmd:
        text = __update_ref__
    return text.encode()


networks = {}
names = {}
containers = {}


def cid(short=False):
    n_chars = 12 if short else 64
    return random.sample("0123456789abcdef" * 10, n_chars)


def run(cmd, **_):
    code, text = 0, ""
    if "docker network create" in cmd:
        name = cmd.split()[-1]
        networks[name] = True
    elif "docker network ls" in cmd:
        name = cmd.split("grep")[1]
        if name in networks:
            text = f"{cid(short=True)}   {name}   bridge    local"
        else:
            code = 1
    elif "docker network rm" in cmd:
        name = text = cmd.split(" rm ")[1].split("|")[0].strip()
        if name not in networks:
            text = "No such net"
    elif "docker stop -t 1" in cmd:
        name = text = cmd.split()[-1]
        if name not in containers and name not in names:
            cmd = 1
            text = f"Error response from daemon: No such container: {name}"
    elif "docker run -d" in cmd:
        name = cmd.split("--name")[1].strip().split()[0]
        containers[name] = text = cid()
    return ProcMock(returncode=code, stdout=text.encode())


subprocess.check_output = check_output
subprocess.run = run
