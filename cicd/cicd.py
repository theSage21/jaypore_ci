from jaypore_ci import jci

with jci.Pipeline(image="Will set later", timeout=15 * 60) as p:
    p.image = image = f"jaypore_image_{p.remote.sha}"
    # Build image
    p.job(
        f"docker build -t {image} .",
        image="arjoonn/jaypore_ci:latest",
        name="Docker build",
    )
    # Run jobs
    p.job("pwd", name="Pwd", depends_on=["Docker build"])
    p.job("tree", name="Tree", depends_on=["Docker build"])
    p.job("python3 -m black --check .", name="Black", depends_on=["Docker build"])
    p.job(
        "python3 -m pylint jaypore_ci/ tests/",
        name="PyLint",
        depends_on=["Docker build"],
    )
    p.job("python3 -m pytest tests/", name="PyTest", depends_on=["Docker build"])
    # Run the pipe
    p.run()
