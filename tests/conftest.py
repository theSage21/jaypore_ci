import os
import json
import unittest

import pytest
import tests.subprocess_mock  # pylint: disable=unused-import
from tests.requests_mock import Mock

from jaypore_ci import jci, executors, remotes, reporters, repos


def add_gitea_mocks(gitea):
    ISSUE_ID = 1
    # --- create PR
    create_pr_url = f"{gitea.api}/repos/{gitea.owner}/{gitea.repo}/pulls"
    Mock.post(create_pr_url, body="", status=201)
    Mock.post(create_pr_url, body="issue_id:{ISSUE_ID}", status=409)
    # --- get existing body
    Mock.get(
        f"{gitea.api}/repos/{gitea.owner}/{gitea.repo}/pulls/{ISSUE_ID}",
        body=json.dumps({"body": "Previous body in PR description."}),
        content_type="application/json",
    )
    # --- update body
    Mock.patch(f"{gitea.api}/repos/{gitea.owner}/{gitea.repo}/pulls/{ISSUE_ID}")
    # --- set commit status
    Mock.post(f"{gitea.api}/repos/{gitea.owner}/{gitea.repo}/statuses/{gitea.sha}")
    Mock.gitea_added = True


def add_github_mocks(github):
    ISSUE_ID = 1
    # --- create PR
    create_pr_url = f"{github.api}/repos/{github.owner}/{github.repo}/pulls"
    Mock.post(create_pr_url, body="", status=404)
    Mock.get(
        create_pr_url,
        body=json.dumps([{"number": ISSUE_ID}]),
        content_type="application/json",
    )
    Mock.post(create_pr_url, body="issue_id:{ISSUE_ID}", status=409)
    # --- get existing body
    Mock.get(
        f"{github.api}/repos/{github.owner}/{github.repo}/pulls/{ISSUE_ID}",
        body=json.dumps({"body": "Already existing body in PR description."}),
        content_type="application/json",
    )
    # --- update body
    Mock.patch(f"{github.api}/repos/{github.owner}/{github.repo}/pulls/{ISSUE_ID}")
    # --- set commit status
    Mock.post(f"{github.api}/repos/{github.owner}/{github.repo}/statuses/{github.sha}")
    Mock.github_added = True


def idfn(x):
    name = []
    for _, item in sorted(x.items()):
        what, _, cls = str(item).replace(">", "").split(".")[-3:]
        name.append(".".join([what, cls]))
    return str(name)


@pytest.fixture(
    scope="function",
    params=list(
        jci.Pipeline.env_matrix(
            reporter=[reporters.Text, reporters.Mock, reporters.Markdown],
            remote=[
                remotes.Mock,
                remotes.Email,
                remotes.GitRemote,
                remotes.Gitea,
                remotes.Github,
            ],
            repo=[repos.Mock, repos.Git],
            executor=[executors.Mock],
        )
    ),
    ids=idfn,
)
def pipeline(request):
    os.environ["JAYPORE_GITEA_TOKEN"] = "fake_gitea_token"
    os.environ["JAYPORE_GITHUB_TOKEN"] = "fake_github_token"
    os.environ["JAYPORE_EMAIL_ADDR"] = "fake@email.com"
    os.environ["JAYPORE_EMAIL_PASSWORD"] = "fake_email_password"
    os.environ["JAYPORE_EMAIL_TO"] = "fake.to@mymailmail.com"
    kwargs = {}
    if request.param["repo"] == repos.Mock:
        kwargs["repo"] = repos.Mock.from_env(
            files_changed=[],
            branch="test_branch",
            sha="fake_sha",
            remote="https://fake_remote.com/fake_owner/fake_repo.git",
            commit_message="fake_commit_message",
        )
    else:
        kwargs["repo"] = request.param["repo"].from_env()
    # --- remote
    kwargs["remote"] = request.param["remote"].from_env(repo=kwargs["repo"])
    if request.param["remote"] == remotes.Gitea and not Mock.gitea_added:
        add_gitea_mocks(kwargs["remote"])
    if request.param["remote"] == remotes.Github and not Mock.github_added:
        add_github_mocks(kwargs["remote"])
    kwargs["executor"] = request.param["executor"]()
    kwargs["reporter"] = request.param["reporter"]()
    p = jci.Pipeline(poll_interval=0, **kwargs)
    if request.param["remote"] == remotes.Email:
        with unittest.mock.patch("smtplib.SMTP_SSL", autospec=True):
            yield p
    else:
        yield p
