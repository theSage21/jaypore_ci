import re

ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_logs(logs):
    """
    Clean logs so that they don't have HTML/ANSI color codes in them.
    """
    for old, new in [("<", r"\<"), (">", r"\>"), ("`", '"'), ("\r", "\n")]:
        logs = logs.replace(old, new)
    return [line.strip() for line in ansi_escape.sub("", logs).split("\n")]
