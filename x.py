from jayporeci.shortcuts import run

with run() as sch:
    sch.job("lint", "black --check .")

    with sch.stage("Building"):
        sch.job("build_rs", "cargo build")
        sch.job("site_build", "npm run build")

    with sch.stage("Testing"):
        sch.job("test_api", "pytest .")
        sch.job("test_ui", "npm run tests")
        sch.job(
            "integration",
            "bash cicd/run_integration.sh",
            after=["test_api", "test_ui"],
        )
