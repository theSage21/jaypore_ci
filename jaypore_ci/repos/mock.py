from typing import List

from jaypore_ci.interfaces import Repo


class Mock(Repo):
    def __init__(self, *, files_changed, **kwargs):
        super().__init__(**kwargs)
        self.files_changed = files_changed

    def files_changed(self, target: str) -> List[str]:
        "Returns list of files changed between current sha and target"
        return self.files_changed

    @classmethod
    def from_env(cls, **kwargs) -> "Mock":
        """
        Gets repo status from the environment and git repo on disk.
        """
        return cls(**kwargs)
