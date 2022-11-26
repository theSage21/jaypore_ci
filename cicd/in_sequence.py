"""
This is one of the simplest pipelines we can have.

It runs jobs one after the other.
"""
from jaypore_ci import jci

p = jci.Pipeline(image="python:3.11", timeout="15m")

assert p.in_sequence(
    p.job("python3 -m black ."),
    p.job("python3 -m pylint src"),
    p.job("python3 -m pytest tests"),
).ok()
