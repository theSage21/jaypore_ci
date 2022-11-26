"""
This pipeline runs jobs in parallel and waits for all of them to finish.
"""
from jaypore_ci import jci

p = jci.Pipeline(image="python:3.11", timeout="15m")

assert p.in_parallel(
    p.job("python3 -m black ."),
    p.job("python3 -m pylint src"),
    p.job("python3 -m pytest tests"),
).ok()
