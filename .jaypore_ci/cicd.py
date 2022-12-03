from jaypore_ci import jci

with jci.Pipeline(image="Will set later", timeout=15 * 60) as p:
    p.image = image = f"jaypore_image_{p.remote.sha}"
    p.in_sequence(
        p.job(
            f"docker build -t {image} .",
            image="arjoonn/jaypore_ci:latest",
            name="Docker build",
        ),
        p.in_parallel(
            p.job("pwd", name="Pwd"),
            p.job("tree", name="Tree"),
            p.job("python3 -m black --check .", name="Black"),
            p.job("python3 -m pylint jaypore_ci/ tests/", name="PyLint"),
            p.job("python3 -m pytest tests/", name="PyTest"),
        ),
    ).should_pass()
