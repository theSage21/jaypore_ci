import pytest

from jaypore_ci import jci, executors, remotes


@pytest.fixture(scope="function")
def pipeline():
    executor = executors.Mock()
    remote = remotes.Mock(branch="test_branch", sha="fake")
    p = jci.Pipeline(executor=executor, remote=remote, poll_interval=0)
    p.render_report = lambda: ""
    yield p
