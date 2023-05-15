from jayporeci.shortcuts import run
from rich import print

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

    with sch.stage("Publishing"):
        sch.job("pub_pypi", "pytest .")
        sch.job("pub_docs", "npm run tests")
        sch.job(
            "downstream_prs",
            "bash notify.sh",
            after=["pub_pypi", "pub_docs"],
        )
        sch.job(
            "notify_cust",
            "bash notify.sh",
            after=["downstream_prs"],
        )
    print(sch.pipeline)
