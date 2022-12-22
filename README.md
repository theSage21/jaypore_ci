# Jaypore CI

> A CI system that sounds ancient and powerful.
> Like the city of Jaypore.

## Expected usage

```bash
curl https://raw.githubusercontent.com/theSage21/jaypore_ci/main/setup.sh | bash
```

- Use the script to install this in any project.
- Configure CI at `cicd/cicd.py`
- Each git-push will trigger a CI job.

## Screenshot

![example screenshot](example.png)

## Examples


- <details>
    <summary>Many jobs in parallel</summary>
 
    ```python
    from jaypore_ci import jci

    with jci.Pipeline() as p:
        p.job("Black", "python3 -m black --check .")
        p.job("Pylint", "python3 -m pylint jaypore_ci/ tests/")
        p.job("PyTest", "python3 -m pytest tests/")
    ```
    </summary>
  </details>
- <details>
    <summary>Running tests with dependencies cached in docker</summary>
 
    ```python
    from jaypore_ci import jci

    with jci.Pipeline() as p:
        image = f"myproject_{p.remote.sha}"
        p.job("Docker", f"docker build -t {image} .")
        p.job("PyTest", "python3 -m pytest tests/", depends_on=["PyTest"])
    ```
    </summary>
  </details>
- <details>
    <summary>Complex job dependencies</summary>
 
    ```python
    from jaypore_ci import jci

    with jci.Pipeline() as p:
        image = f"myproject_{p.remote.sha}"
        with p.stage("build"):
            p.job("DockProd", f"docker build --target ProdEnv -t {image}_prod .")
            p.job("DockDev", f"docker build --target DevEnv -t {image}_dev .")
        with p.stage("checking"):
            p.job("UnitTest", "python3 -m pytest -m unit tests/")
            p.job("PyLint", "python3 -m pylint src/")
            p.job("Black", "python3 -m black --check .")
            p.job(
                "IntegrationTest",
                "python3 -m pytest -m integration tests/",
                depends_on=["PyLint", "UnitTest"],
            )
        with p.stage("publish"):
            p.job("TagProd", f"docker tag -t {image}_prod hub/{image}_prod:{p.remote.sha}")
            p.job("TagDev", f"docker tag -t {image}_dev hub/{image}_dev:{p.remote.sha}")
            p.job(
                "PushProd",
                f"docker push hub/{image}_prod:{p.remote.sha}",
                depends_on=["TagProd"],
            )
            p.job(
                "PushDev",
                f"docker push hub/{image}_dev:{p.remote.sha}",
                depends_on=["TagDev"],
            )
    ```
    </summary>
  </details>
- <details>
    <summary>Job matrix</summary>
 
    ```python
    from jaypore_ci import jci

    with jci.Pipeline() as p:
        # This will have 18 jobs
        # one for each possible combination of BROWSER, SCREENSIZE, ONLINE
        for env in p.env_matrix(
            BROWSER=["firefox", "chromium", "webkit"],
            SCREENSIZE=["phone", "laptop", "extended"],
            ONLINE=["online", "offline"],
        ):
            p.job(f"Test: {env}", "python3 -m pytest tests", env=env)
    ```
    </summary>
  </details>
- <details>
    <summary>TLDR: Running jobs on cloud</summary>

    - We can get the remote machine's docker socket by using [ssh socket forwarding](https://medium.com/@dperny/forwarding-the-docker-socket-over-ssh-e6567cfab160)
    - Then we can set jaypore CI to use the remote docker socket by editing `cicd/pre-push.githook`
    </summary>
  </details>
- <details>
    <summary>With a db service in background</summary>
 
    ```python
    from jaypore_ci import jci

    # Services immediately return with a PASSED status
    # If they exit with a Non ZERO code they are marked as FAILED, otherwise
    # they are assumed to be PASSED
    with jci.Pipeline() as p:
        with p.stage("Services", is_service=True):
            p.job("Mysql", None, image="mysql")
            p.job("Redis", None, image="redis")
            p.job("Api", "python3 -m src.run_api", image="python:3.11")
        with p.stage("Testing"):
            p.job("UnitTest", "python3 -m pytest -m unit_tests tests")
            p.job("IntegrationTest", "python3 -m pytest -m integration_tests tests")
            p.job("RegressionTest", "python3 -m pytest -m regression_tests tests")
    ```
    </summary>
  </details>
