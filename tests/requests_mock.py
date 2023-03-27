import json
import requests

from typing import NamedTuple, Callable, List
from collections import defaultdict

from jaypore_ci.remotes import Gitea, Github


class MockResponse(NamedTuple):
    status_code: int
    body: str
    content_type: str

    def json(self) -> str:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body


class Mock:
    registry = defaultdict(list)
    index = defaultdict(int)
    gitea_remotes: List[str] = []
    github_remotes: List[str] = []

    @classmethod
    def get(
        cls,
        url: str,
        status: int = 200,
        body: str = "",
        content_type: str = "text/html",
    ) -> None:
        cls.registry["get", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def post(
        cls,
        url: str,
        status: int = 200,
        body: str = "",
        content_type: str = "text/html",
    ) -> None:
        cls.registry["post", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def patch(
        cls,
        url: str,
        status: int = 200,
        body: str = "",
        content_type: str = "text/html",
    ) -> None:
        cls.registry["patch", url].append(
            MockResponse(status_code=status, body=body, content_type=content_type)
        )

    @classmethod
    def handle(cls, method: str) -> Callable:
        def handler(url: str, **_):
            options = cls.registry[method, url]
            index = cls.index[method, url]
            resp = options[index]
            cls.index[method, url] = (cls.index[method, url] + 1) % len(options)
            return resp

        return handler


def add_gitea_mocks(gitea: Gitea, remote_url: str) -> None:
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
    Mock.gitea_remotes.append(remote_url)


def add_github_mocks(github: Github, remote_url: str) -> None:
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
    Mock.github_remotes.append(remote_url)


requests.get = Mock.handle("get")
requests.post = Mock.handle("post")
requests.patch = Mock.handle("patch")
