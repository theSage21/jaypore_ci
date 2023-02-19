import pytest

from jaypore_ci import jci, executors, remotes, reporters, repos


@pytest.fixture(
    scope="function", params=[reporters.Text, reporters.Mock, reporters.Markdown]
)
def pipeline(request):
    repo = repos.Mock.from_env(
        files_changed=[], branch="test_branch", sha="fake_sha", remote="fake_remote"
    )
    executor = executors.Mock()
    remote = remotes.Mock(branch=repo.branch, sha=repo.sha)
    reporter = request.param()
    p = jci.Pipeline(
        repo=repo, executor=executor, remote=remote, reporter=reporter, poll_interval=0
    )
    p.render_report = lambda: ""
    yield p
