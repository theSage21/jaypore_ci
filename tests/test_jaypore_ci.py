import pytest
from jaypore_ci.changelog import version_map
from jaypore_ci.config import const


def test_sanity():
    assert 4 == 2 + 2


def test_version_has_entry_in_version_map():
    assert const.version in version_map, const


def test_simple_linear_jobs(pipeline):
    pipeline = pipeline()
    with pipeline as p:
        p.job("lint", "x")
        p.job("test", "x", depends_on=["lint"])
    order = pipeline.executor.get_execution_order()
    assert order["lint"] < order["test"]


def test_no_duplicate_names(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("lint", "x")
            p.job("lint", "y")


def test_dependency_has_to_be_defined_before_child(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", "x", depends_on=["y"])
            p.job("y", "y")


def test_dependency_cannot_cross_stages(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("stage1"):
                p.job("y", "y")
            with p.stage("stage2"):
                p.job("x", "x", depends_on=["y"])


def test_duplicate_stages_not_allowed(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("stage1"):
                p.job("x", "x")
            with p.stage("stage1"):
                p.job("y", "y")


def test_stage_and_job_cannot_have_same_name(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("x"):
                p.job("x", "x")


def test_cannot_define_duplicate_jobs(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", "x")
            p.job("x", "x")


def test_non_service_jobs_must_have_commands(pipeline):
    pipeline = pipeline()
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", None)


def test_call_chain_is_followed(pipeline):
    pipeline = pipeline()
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


def test_env_matrix_is_easy_to_make(pipeline):
    pipeline = pipeline()
    with pipeline as p:
        for i, env in enumerate(p.env_matrix(A=[1, 2, 3], B=[5, 6, 7])):
            p.job(f"job{i}", "fake command", env=env)
    assert len(pipeline.jobs) == 9
