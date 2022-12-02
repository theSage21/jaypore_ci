from jaypore_ci import jci

with jci.Pipeline(
    image="arjoonn/jaypore_ci:latest",  # NOTE: Change this to whatever you need
    timeout=15 * 60,
) as p:
    p.in_parallel(
        p.job("pwd", name="Pwd"),
        p.job("tree", name="Tree"),
        p.job("python3 -m black --check .", name="Black"),
        p.job("python3 -m pylint jaypore_ci/ tests/", name="PyLint"),
        p.job("python3 -m pytest tests/", name="PyTest"),
    ).should_pass()
