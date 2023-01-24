import pytest

from jaypore_ci import jci, executors, remotes, reporters


@pytest.fixture(
    scope="function", params=[reporters.Text, reporters.Mock, reporters.Markdown]
)
def pipeline(request):
    executor = executors.Mock()
    remote = remotes.Mock(branch="test_branch", sha="fake")
    reporter = request.param()
    p = jci.Pipeline(
        executor=executor, remote=remote, reporter=reporter, poll_interval=0
    )
    p.render_report = lambda: ""
    yield p
