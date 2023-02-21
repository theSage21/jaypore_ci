import random
import subprocess


def sha():
    return hex(random.getrandbits(128))


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
        text = sha()
    elif "git log -1" in cmd:
        text = "some_fake_git_commit_message\nfrom_subprocess_mock"
    # jci
    elif "cat /proc/self/cgroup" in cmd:
        text = "fake_pipe_id_from_subprocess_mock"
    # remotes.git
    elif "git hash-object" in cmd:
        text = sha()
    elif "git mktree" in cmd:
        text = sha()
    elif "git commit-tree" in cmd:
        text = sha()
    elif "git update-ref" in cmd:
        text = sha()
    return text.encode()


subprocess.check_output = check_output
