import json

from typing import NamedTuple
from collections import defaultdict

import requests


class MockResponse(NamedTuple):
    status_code: int
    body: str
    content_type: str

    def json(self):
        return json.loads(self.body)

    @property
    def text(self):
        return self.body


class Mock:
    registry = defaultdict(list)
    index = defaultdict(int)
    gitea_added = False
    github_added = False

    @classmethod
    def get(cls, url, status=200, body="", content_type="text/html"):
        cls.registry["get", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def post(cls, url, status=200, body="", content_type="text/html"):
        cls.registry["post", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def patch(cls, url, status=200, body="", content_type="text/html"):
        cls.registry["patch", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def handle(cls, method):
        def handler(url, **_):
            options = cls.registry[method, url]
            index = cls.index[method, url]
            resp = options[index]
            cls.index[method, url] = (cls.index[method, url] + 1) % len(options)
            return resp

        return handler


def add_gitea_mocks(gitea):
    ISSUE_ID = 1
    # --- create PR
    create_pr_url = f"{gitea.api}/repos/{gitea.owner}/{gitea.repo}/pulls"
    Mock.post(create_pr_url, body="", status=201)
    Mock.post(create_pr_url, body=f"issue_id:{ISSUE_ID}", status=409)
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
    Mock.post(create_pr_url, body=f"issue_id:{ISSUE_ID}", status=409)
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


requests.get = Mock.handle("get")
requests.post = Mock.handle("post")
requests.patch = Mock.handle("patch")
