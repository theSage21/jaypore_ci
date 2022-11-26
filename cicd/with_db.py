"""
For example if you want to test your api server and need a database to run
in order to do that.

In this example we will run tests for a project that requires a redis server
and a postgres server.
"""
from jaypore_ci import jci

p = jci.Pipeline(
    image="python:3.11",
    timeout="15m",
    # These variables are available to the entire pipeline
    env={"POSTGRES_PASSWORD": "simplepassword"},
)

with p.services(
    p.job(image="redis"),
    p.job(
        image="postgres",
        # These variables can be used to configure the service
        env={"POSTGRES_INITDB_ARGS": "--data-checksums"},
    ),
):
    assert p.in_sequence(
        p.job("python3 -m myrepo.run_migrations"),
        p.job(
            "python3 -m pytest tests",
            # These variables are merged with pipeline variables.
            env={"APP_REDIS_HOST": "redis", "APP_POSTGRES_HOST": "postgres"},
        ),
    ).ok()
