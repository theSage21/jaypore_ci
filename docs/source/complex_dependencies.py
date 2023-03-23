from jaypore_ci import jci

with jci.Pipeline() as p:

    with p.stage("build"):
        p.job("DockDev", f"docker build --target DevEnv -t {p.repo.sha}_dev .")

    with p.stage("checking", image=f"{p.repo.sha}_dev"):
        p.job("Integration", "run test.sh integration")
        p.job("Unit", "run test.sh unit")
        p.job("Linting", "run lint.sh")
        p.job(
            "Fuzz testing",
            "bash test.sh fuzz",
            depends_on=["Integration", "Unit"],
        )
