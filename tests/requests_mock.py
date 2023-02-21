from typing import NamedTuple
from collections import defaultdict

import requests


class MockResponse(NamedTuple):
    status_code: int
    body: str
    content_type: str


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
            resp = options[cls.index[method, url]]
            cls.index[method, url] = (cls.index[method, url] + 1) % len(options)
            return resp

        return handler


requests.get = Mock.handle("get")
requests.post = Mock.handle("post")
requests.patch = Mock.handle("patch")
