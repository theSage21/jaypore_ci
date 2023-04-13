import subprocess


def run(args, **kwargs):
    """
    Add common options for subprocess calls.
    """
    kwargs["shell"] = True
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.STDOUT
    kwargs["check"] = False
    return subprocess.run(args, **kwargs)
