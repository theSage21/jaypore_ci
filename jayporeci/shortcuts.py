from .impl import (
    SimpleScheduler,
    DockerExecutor,
    ConsolePlatform,
    TextReporter,
    GitRepo,
)
from .definitions import Pipeline


def run():
    """
    A shorthand way to define a combination of
    :class:`~jayporeci.definitions.Pipeline`,
    :class:`~jayporeci.definitions.Executor`,
    :class:`~jayporeci.definitions.Remote`,
    :class:`~jayporeci.definitions.Reporter`,
    :class:`~jayporeci.definitions.Repo`.

    If you need to declare a non-default combination of these objects, please
    create them manually. See the source code of this function to understand
    how the objects fit together.
    """

    repo = GitRepo.from_env()
    sch = SimpleScheduler(
        pipeline=Pipeline.create(repo=repo),
        platform=ConsolePlatform(repo=repo),
        reporter=TextReporter(),
        executor=DockerExecutor(sha=repo.sha),
    )
    return sch
