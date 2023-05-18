import pytest
from . import factories


def ok():
    "Return a command that will run successfully"
    return "bash -c 'echo success'"


def ex(n=1):
    "Return a command that return the exit code that is provided."
    return f"bash -c 'exit {n}'"


@pytest.fixture(scope="function", params=factories.configs(), ids=str)
def config(request):
    yield request.param
