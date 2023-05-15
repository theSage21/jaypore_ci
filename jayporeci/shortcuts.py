from jayporeci.definitions import (
    Pipeline,
    Executor,
    Platform,
    Reporter,
    Repo,
    Scheduler,
)


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

    sch = Scheduler(
        pipeline=Pipeline(repo=Repo.from_env()),
        platform=Platform(),
        reporter=Reporter(),
        executor=Executor(),
    )
    return sch
