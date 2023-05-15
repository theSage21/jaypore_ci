from .impl import (
    SimpleScheduler,
    DockerExecutor,
    CliPlatform,
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

    sch = SimpleScheduler(
        pipeline=Pipeline(repo=GitRepo.from_env()),
        platform=CliPlatform(),
        reporter=TextReporter(),
        executor=DockerExecutor(),
    )
    return sch
