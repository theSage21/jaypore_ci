from jaypore_ci import jci

# Services immediately return with a PASSED status
# If they exit with a Non ZERO code they are marked as FAILED, otherwise
# they are assumed to be PASSED
with jci.Pipeline() as p:
    # Since we define all jobs in this section as `is_service=True`, they will
    # keep running for as long as the pipeline runs.
    with p.stage("Services", is_service=True):
        p.job("Mysql", None, image="mysql")
        p.job("Redis", None, image="redis")
        p.job("Api", "python3 -m src.run_api", image="python:3.11")

    with p.stage("Testing"):
        p.job("Unit", "pytest -m unit_tests tests")
        p.job("Integration", "pytest -m integration_tests tests")
        p.job("Regression", "pytest -m regression_tests tests")
