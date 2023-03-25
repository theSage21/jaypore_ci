from jaypore_ci import jci

with jci.Pipeline() as p:
    # This will have 18 jobs
    # one for each possible combination of BROWSER, SCREENSIZE, ONLINE
    for env in p.env_matrix(
        BROWSER=["firefox", "chromium", "webkit"],
        SCREENSIZE=["phone", "laptop", "extended"],
        ONLINE=["online", "offline"],
    ):
        p.job(
            f"Test: {env}",
            "pytest --browser=$BROWSER --device=$SCREENSIZE",
            env=env,
        )
