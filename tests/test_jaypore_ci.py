import pytest


def test_sanity():
    assert 4 == 2 + 2


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


def test_dependency_cannot_cross_stages(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("stage1"):
                p.job("y", "y")
            with p.stage("stage2"):
                p.job("x", "x", depends_on=["y"])


def test_duplicate_stages_not_allowed(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("stage1"):
                p.job("x", "x")
            with p.stage("stage1"):
                p.job("y", "y")


def test_stage_and_job_cannot_have_same_name(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            with p.stage("x"):
                p.job("x", "x")


def test_cannot_define_duplicate_jobs(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", "x")
            p.job("x", "x")


def test_non_service_jobs_must_have_commands(pipeline):
    with pytest.raises(AssertionError):
        with pipeline as p:
            p.job("x", None)


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


def test_env_matrix_is_easy_to_make(pipeline):
    with pipeline as p:
        for i, env in enumerate(p.env_matrix(A=[1, 2, 3], B=[5, 6, 7])):
            p.job(f"job{i}", "fake command", env=env)
    assert len(pipeline.jobs) == 9
