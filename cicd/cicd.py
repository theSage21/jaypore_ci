from jaypore_ci import jci

with jci.Pipeline() as p:
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
    with p.stage("Publish", image=jcienv):
        p.job("DockerHubJcienv", "bash cicd/build_and_push_docker.sh jcienv")
        p.job("DockerHubJci", "bash cicd/build_and_push_docker.sh jci")
        p.job("PublishDocs", f"bash cicd/build_and_publish_docs.sh {p.remote.branch}")
        p.job("PublishPypi", "bash cicd/build_and_push_pypi.sh")
