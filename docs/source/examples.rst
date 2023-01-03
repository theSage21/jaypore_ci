Examples
========

This document lists things that you can do using JayporeCI

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

- Make sure docker is installed on the remote machine.
- Make sure you have ssh access to remote machine and the user you are logging in as can run docker commands.
- Add to your local `~.ssh/config` an entry for your remote machine. Something like:

  .. code-block:: config

    Host my.aws.machine
        HostName some.aws.machine
        IdentityFile ~/.ssh/id_rsa
- Now in your `cicd/pre-push.sh` file, where the `docker run` command is mentioned, simply add `DOCKER_HOST=ssh://my.aws.machine`
- JayporeCi will then run on the remote machine.

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

Common jobs for multiple git repos
----------------------------------

- Sometimes we need to enforce common jobs for multiple git projects. A few examples:
- A common lint policy for company / clients.
- Common deploy targets and processes for things like docs / release notes.
- Common locations for built targets / artifact caches. 
- Common notification targets like slack / telegram / email.
- Common PR description checklist for company / clients.
- Common PR merge policies / review policies etc.

Since `JayporeCI` has a normal programming language as it's config language, these things can be solved without too much effort.

1. Create a custom python file and add your common jobs to a function in that
   file. For example if we want to make sure that `Black
   <https://github.com/psf/black>`_ is the code formatter for all your
   projects:

    .. code-block:: python
       
       # mycommonjobs.py
       def add_common_lint_jobs(p):
           p.job("black", "python3 -m black --check .")
    
2. Create your own docker file based on top of `arjoonn/jci:latest` and add your own code to it. For example:

    .. code-block:: dockerfile

        from arjoonn/jci:latest
        run python -m pip install black
        add mycommonjobs.py .
   
   After this you can build and publish this image to dockerhub. If you don't
   want to publish this image you can simply make sure that it is available on
   the machine that will run your CI.

3. Now in any project you can use this docker image in `cicd/pre-push.sh`
   instead of `arjoonn/jci:latest`. For example if you pushed this image to
   dockerhub with the name `myown/jobs:latest` then you can edit
   your `cicd/pre-push.sh` file to have the docker run command look something
   like this:

    .. code-block:: bash

        docker run -d \
            # ... Other parameters as it is ...
            myown/jobs:latest \ # Instead of arjoonn/jci:latest
            # ... Other parameters as it is ...

4. Inside `cicd/cicd.py` you can now simply import and call your common code function to add those common jobs:

    .. code-block:: python

       from jaypore_ci import jci
       from mycommonjobs import add_common_lint_jobs

       with jci.Pipeline() as p:
           add_common_lint_jobs(p)
           # ---
           p.job("Test", "pytest -m unit_tests tests")
