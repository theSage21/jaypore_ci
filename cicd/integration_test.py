"""
This example shows how integration testing can be done using:
    - Your own API
    - A static site built and served
    - A postgres database
    - A redis server
    - Your own integration tests
"""
from jaypore_ci import jci

p = jci.Pipeline(
    image="python:3.11",
    timeout="15m",
    env={"DB_PWD": "simplepassword"},
)

with p.services(
    p.job(name="Redis cache", image="redis"),
    p.job(name="Database", image="postgres"),
    p.job(
        "yarn install",
        "yarn build",
        "python3 -m http.server",
        name="Static site",
        image="my/reactjs_env:v0.1",
    ),
    p.job(
        "python3 -m api",
        name="API service",
        image="my/django_env:v0.1",
    ),
):
    assert p.in_sequence(
        p.job("python3 -m wait_for_services_to_be_up"),
        p.job("python3 -m myrepo.run_migrations"),
        p.job("python3 -m pytest tests -m integration_tests"),
    ).ok()
