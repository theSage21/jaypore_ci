import pytest

from jaypore_ci import __version__


def test_version():
    assert __version__ == "0.1.0"


def test_simple_linear_jobs(pipeline):
    with pipeline as p:
        p.job("lint", "x")
        p.job("test", "x", depends_on=["lint"])
    lint_i = [i for i, *_ in pipeline.executor.get_log("lint")]
    test_i = [i for i, *_ in pipeline.executor.get_log("test")]
    assert all(lint < test for lint in lint_i for test in test_i)


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
