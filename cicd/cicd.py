from jaypore_ci import jci
from typing import NamedTuple


class Should(NamedTuple):
    release: bool = False
    lint: bool = False


def parse_commit(repo):
    """
    Decide what all the commit is asking us to do.
    """
    config = {}
    for line in repo.commit_message.lower().split("\n"):
        line = line.strip().replace(" ", "")
        if "jci:" in line:
            _, key = line.split("jci:")
            config[key] = True
    return Should(**config)


with jci.Pipeline() as p:
    should = parse_commit(p.repo)
    jcienv = f"jcienv:{p.repo.sha}"
    with p.stage("build_and_test"):
        p.job("JciEnv", f"docker build  --target jcienv -t jcienv:{p.repo.sha} .")
        p.job(
            "Jci",
            f"docker build  --target jci -t jci:{p.repo.sha} .",
            depends_on=["JciEnv"],
        )
        kwargs = dict(image=jcienv, depends_on=["JciEnv"])
        p.job("black", "python3 -m black --check .", **kwargs)
        p.job("pylint", "python3 -m pylint jaypore_ci/ tests/", **kwargs)
        p.job("pytest", "bash cicd/run_tests.sh", image=jcienv, depends_on=["JciEnv"])

    if should.release:
        with p.stage("Publish", image=jcienv):
            p.job("DockerHubJcienv", "bash cicd/build_and_push_docker.sh jcienv")
            p.job("DockerHubJci", "bash cicd/build_and_push_docker.sh jci")
            p.job(
                "PublishDocs", f"bash cicd/build_and_publish_docs.sh {p.remote.branch}"
            )
            p.job("PublishPypi", "bash cicd/build_and_push_pypi.sh")
