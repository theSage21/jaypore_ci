import pytest

from jaypore_ci import jci, executors, remotes


@pytest.fixture(scope="function")
def pipeline():
    executor = executors.Mock()
    remote = remotes.Mock(branch="test_branch", sha="fake")
    yield jci.Pipeline(executor=executor, remote=remote, poll_interval=0)
