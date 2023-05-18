import random
from jayporeci.impl import (
    SimpleScheduler,
    DockerExecutor,
    ConsolePlatform,
    TextReporter,
    GitRepo,
)
from jayporeci.definitions import Pipeline


def configs():
    for repo in repos():
        SC = SimpleScheduler(
            pipeline=Pipeline(repo=repo),
            platform=ConsolePlatform(repo=repo),
            reporter=TextReporter(),
            executor=DockerExecutor(sha=repo.sha),
        )
        sch.__run_on_exit__ = False
        with SC() as sch:
            for stage in range(10):
                known_jobs = set()
                with sch.stage(f"Stage:{stage}"):
                    for job in range(10):
                        ex = random.choice([0, 1])
                        af = random.choice(range(len(known_jobs))) if known_jobs else 0
                        af = random.sample(known_jobs, af) if af else None
                        sch.job(f"Job:{stage}:{job}", f"bash -c 'exit {ex}'", after=af)
        yield SC


def repos():
    for sha in [
        "76b59cd9808bb8ed536a64d7b07af0aac9d6a9033cf2d0a88013f1244f774f95",
        "ead2ffdf4aa36c564d774dd9f7e89eb2645e13c8f34aef7aacc708c5a4cad20b",
    ]:
        for branch in ["develop", "feature1", "some"]:
            for remote in [
                "ssh://git@gitea.jayporeci.in:arjoonn/jaypore_ci.git",
                "ssh+git://git@gitea.jayporeci.in:arjoonn/jaypore_ci.git",
                "git@gitea.jayporeci.in:arjoonn/jaypore_ci.git",
                "https://gitea.jayporeci.in/midpath/jaypore_ci.git",
                "http://gitea.jayporeci.in/midpath/jaypore_ci.git",
            ]:
                for commit_message in [
                    "x",
                    "some commit message",
                    "a very long commit message that keeps on repeating" * 1000,
                ]:
                    yield GitRepo(
                        sha=sha,
                        branch=branch,
                        remote=remote,
                        commit_message=commit_message,
                    )
