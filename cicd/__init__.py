from jaypore_ci import jci

pipe = jci.Pipeline(image="python:3.11", timeout="15m")
assert pipe.job("python3 -m cicd.commit_msg_has_issue_number").run().ok()
assert (
    pipe.parallel(
        pipe.job("python3 -m black ."),
        pipe.job("python3 -m pylint src"),
        pipe.job("python3 -m pytest tests"),
    )
    .run()
    .ok()
)
