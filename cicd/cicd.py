from jaypore_ci import jci


with jci.Pipeline() as p:
    jcienv = f"jcienv:{p.remote.sha}"
    with p.stage("Docker"):
        p.job("JciEnv", f"docker build  --target jcienv -t {jcienv} .")
        p.job("Jci", f"docker build  --target jci -t jci:{p.remote.sha} .")
    with p.stage("Checks", image=jcienv):
        p.job("black", "python3 -m black --check .")
        p.job("pylint", "python3 -m pylint jaypore_ci/ tests/")
        p.job("pytest", "python3 -m pytest tests/")
