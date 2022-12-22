from jaypore_ci import jci


with jci.Pipeline() as p:
    jcienv = f"jcienv:{p.remote.sha}"
    with p.stage("Docker"):
        p.job("JciEnv", f"docker build  --target jcienv -t jcienv:{p.remote.sha} .")
        p.job("Jci", f"docker build  --target jci -t jci:{p.remote.sha} .")
    with p.stage("Jobs", image=jcienv):
        p.job("black", "python3 -m black --check .")
        p.job("pylint", "python3 -m pylint jaypore_ci/ tests/")
        p.job("pytest", "python3 -m pytest tests/")
    with p.stage("Publish", image=jcienv):
        # docs
        p.job("BuildDocs", "sphinx-build -b html docs/source/ docs/build/html")
        p.job("PublishDocs", "bash -c 'echo hi'", depends_on=["BuildDocs"])
        # pypi
        p.job("PoetryBuild", "poetry build")
        p.job("PoetryPublish", "poetry publish", depends_on=["PoetryBuild"])
        # jcienv
        p.job(
            "DockerTagJcienv",
            "docker tag -t jcienv:{p.remote.sha} arjoonn/jcienv:{p.remote.sha}",
        )
        p.job(
            "DockerPublishJcienv",
            "docker push arjoonn/jcienv:{p.remote.sha}",
            depends_on=["DockerTagJcienv"],
        )
        # jci
        p.job(
            "DockerTagJci",
            "docker tag -t jci:{p.remote.sha} arjoonn/jci:{p.remote.sha}",
        )
        p.job(
            "DockerPublishJci",
            "docker push arjoonn/jci:{p.remote.sha}",
            depends_on=["DockerTagJci"],
        )
