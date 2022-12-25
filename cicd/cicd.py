from jaypore_ci import jci


with jci.Pipeline() as p:
    jcienv = f"jcienv:{p.remote.sha}"
    with p.stage("Docker"):
        p.job("JciEnv", f"docker build  --target jcienv -t jcienv:{p.remote.sha} .")
        p.job("Jci", f"docker build  --target jci -t jci:{p.remote.sha} .")
    with p.stage("Jobs", image=jcienv):
        p.job("PublishDocs", f"bash cicd/build_and_publish_docs.sh {p.remote.branch}")
        p.job("black", "python3 -m black --check .")
        p.job("pylint", "python3 -m pylint jaypore_ci/ tests/")
        p.job("pytest", "python3 -m pytest tests/")
    with p.stage("Publish", image=jcienv):
        p.job("DockerHubJcienv", "bash cicd/build_and_push_docker.sh jcienv")
        p.job("DockerHubJci", "bash cicd/build_and_push_docker.sh jci")
