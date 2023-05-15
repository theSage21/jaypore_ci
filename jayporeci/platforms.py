from .definitions import Platform, Repo, Status


class ConsolePlatform(Platform):
    """
    A mock remote implementation.
    """

    def __init__(self, repo: Repo) -> "ConsolePlatform":
        self.repo = repo

    @classmethod
    def from_env(cls, *, repo: Repo) -> "ConsolePlatform":
        return cls(repo)

    def publish(self, report: str, status: Status):
        print("Published report", status, "\n", report)
