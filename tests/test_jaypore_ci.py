import pytest

from jaypore_ci import __version__


def test_version():
    assert __version__ == "0.1.0"


def test_simple_linear_jobs(pipeline):
    with pipeline as p:
        p.job("lint", "x")
        p.job("test", "x", depends_on=["lint"])
    order = pipeline.executor.get_execution_order()
    assert order["lint"] < order["test"]


def test_no_duplicate_names(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("lint", "x")
            p.job("lint", "y")


def test_dependency_has_to_be_defined_before_child(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", "x", depends_on=["y"])
            p.job("y", "y")


def test_call_chain_is_followed(pipeline):
    with pipeline as p:
        for name in "pq":
            p.job(name, name)
        p.job("x", "x")
        p.job("y", "y", depends_on=["x"])
        p.job("z", "z", depends_on=["y"])
        for name in "ab":
            p.job(name, name)
    order = pipeline.executor.get_execution_order()
    # assert order == {}
    assert order["x"] < order["y"] < order["z"]
