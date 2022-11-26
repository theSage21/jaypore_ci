"""
This example shows how you can run multiple jobs
and make some of them only run when specific files have changed.
"""
from jaypore_ci import jci

p = jci.Pipeline(image="python:3.11", timeout="15m")

assert p.in_parallel(
    p.job("python3 -m black ."),
    (
        p.job("python3 -m pytest tests")
        if p.file_changes_in(*list(p.repo.path.glob("src/*")))
        else None
    ),
    (
        p.job("python3 -m cicd.check_changelog_format")
        if p.file_changes_in(p.repo.path / "CHANGELOG")
        else None
    ),
).ok()
