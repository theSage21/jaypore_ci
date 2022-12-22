Examples
========

Cache env dependencies in docker
--------------------------------

You can cache your environment dependencies in docker easily.

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:
        image = f"myproject:{p.remote.sha}"
        p.job("Docker", f"docker build -t {image} .")
        p.job(
            "PyTest",
            "python3 -m pytest tests/",
            image=image,
            depends_on=["Docker"]
        )


Complex dependencies between jobs
---------------------------------


- A pipeline can have stages.
- Stages are executed one after the other.
- Jobs inside a stage are all run in parallel
  - **unless** a job declares what other jobs it `depends_on`.


For example, this config builds docker images, runs linting, testing on the
codebase, then builds and publishes documentation.


.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:
        image = f"myproject_{p.remote.sha}"

        with p.stage("build"):
            p.job("DockProd", f"docker build --target ProdEnv -t {image}_prod .")
            p.job("DockDev", f"docker build --target DevEnv -t {image}_dev .")

        with p.stage("checking", image=f"{image}_dev"):
            p.job("UnitTest", "python3 -m pytest -m unit tests/")
            p.job("PyLint", "python3 -m pylint src/")
            p.job("Black", "python3 -m black --check .")
            p.job(
                "IntegrationTest",
                "python3 -m pytest -m integration tests/",
                depends_on=["PyLint", "UnitTest"],
            )
            p.job(
                "RegressionTest",
                "python3 -m pytest -m regression tests/",
                depends_on=["PyLint", "UnitTest"],
            )
            p.job(
                "FuzzyTest",
                "python3 -m pytest -m fuzzy tests/",
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
            p.job(
                "BuildDocs",
                "sphinx-build -b html docs/source/ docs/build/html",
                image=f"{image}_dev"
            )


Matrix jobs
-----------
 
There is no special concept for matrix jobs. Just declare as many jobs as you want. There is a function to help you do this though.

.. code-block:: python

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

The above config generates 3 x 3 x 2 = 18 jobs and sets the environment for each to a unique combination of `BROWSER` , `SCREENSIZE`, and `ONLINE`.

Running on cloud/remote machine
-------------------------------

- Since the executor is docker:
    - We can get the remote machine's docker socket by using [ssh socket forwarding](https://medium.com/@dperny/forwarding-the-docker-socket-over-ssh-e6567cfab160)
    - Then we can set Jaypore CI to use the remote docker socket by editing `cicd/pre-push.githook`
- Now all jobs will run on the remote machine.


Having database / other services during CICD
--------------------------------------------


.. code-block:: python

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
