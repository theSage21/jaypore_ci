.. Jaypore CI documentation master file, created by
   sphinx-quickstart on Thu Dec 22 13:34:40 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Jaypore CI Documentation
========================

**Jaypore CI** is a *small*, *very flexible*, and *powerful* system for automation within software projects.


TLDR
----

- Python is the config language.
    - No more debugging YAML configs / escape errors.
    - It's a general purpose programming language! Go wild in how / where / when you want your CI to run.
- Jobs are run via docker; on your laptop.
    - No more debugging why stuff is only working in local.
    - You can exec into a running job / see full logs / inspect and even run a debugger on a live job without too much effort.
- Runs offline so I can work without internet.
    - If needed CAN run on cloud runners.


Contents
--------

.. contents::

Getting Started
========

Installation
------------

You can easily install it using a bash script.

.. code-block:: console

   $ curl https://get.jayporeci.in | bash


**Or** you can manually install it. These names are convention, you can call your folders/files anything.
    
1. Create a directory called *cicd* in the root of your repo.
2. Create a file *cicd/pre-push.sh*
3. Create a file *cicd/cicd.py*
4. Update your repo's pre-push git hook so that it runs the *cicd/pre-push.sh* file when you push.


How it works
------------

1. Git hook calls `cicd/pre-push.sh`
2. After doing some administration stuff, `cicd/pre-push.sh` calls `cicd/cicd.py`
3. As per your config, `cicd/cicd.py` will run your jobs within docker.


Your entire config is inside `cicd/cicd.py`. Edit it to whatever you like! A basic config would look like this:

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline(image='mydocker/image') as p:
        p.job("Black", "black --check .")
        p.job("Pylint", "pylint mycode/ tests/")
        p.job("PyTest", "pytest tests/")

Examples
========


Dependencies in docker
----------------------

Environment / package dependencies can be cached in docker easily. Simply build
your docker image and then run the job with that built image.

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:
        p.job("Docker", f"docker build -t myimage .")
        p.job(
            "PyTest",
            "python3 -m pytest tests/",
            image="myimage",
            depends_on=["Docker"]
        )


Complex job relations
---------------------

- A pipeline can have stages.
- Stages are executed one after the other.
- Jobs inside a stage are all run in parallel **unless** a job declares what other jobs it `depends_on`.
- Keyword arguments can be set at `Pipeline`, `stage`, and `job` level. For
  example you can set `env` vars / what docker image to use and so on.


For example, this config builds docker images, runs linting, testing on the
codebase, then builds and publishes documentation.


.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:
        image = f"myproject_{p.remote.sha}"

        with p.stage("build"):
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


Job matrix
----------
 
There is no special concept for matrix jobs. Just declare as many jobs as you
want in a while loop. There is a function to make this easier when you want to
run combinations of variables.

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

Cloud/remote runners
--------------------

- Make sure docker is installed on the remote machine.
- Make sure you have ssh access to remote machine and the user you are logging in as can run docker commands.
- Add to your local `~.ssh/config` an entry for your remote machine. Something like:

  .. code-block:: config

    Host my.aws.machine
        HostName some.aws.machine
        IdentityFile ~/.ssh/id_rsa
- Now in your `cicd/pre-push.sh` file, where the `docker run` command is mentioned, simply add `DOCKER_HOST=ssh://my.aws.machine`
- JayporeCi will then run on the remote machine.

DB Services
-----------

Some jobs don't affect the status of the pipeline. They just need to be there
while you are running your tests. For example, you might need a DB to run API
testing, or you might need both the DB and API as a service to run integration
testing.

To do this you can add `is_service=True` to the job / stage / pipeline arguments.

Services are only shut down when the pipeline is finished.


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

Import jobs with pip install
----------------------------

You can also import jobs defined by other people. Some examples of why you might want to do this:

- A common lint policy for company / clients.
- Common deploy targets and processes for things like docs / release notes.
- Common notification targets like slack / telegram / email.
- Common PR description checklist for company / clients.
- Common PR merge policies / review policies etc.

Since `JayporeCI` has a normal programming language as it's config language, most things can be solved without too much effort.


Artifacts / Cache
-----------------

- All jobs run in a shared directory `jaypore_ci/run`.
- Anything you write to this directory is available to all jobs so you can use this to pass artifacts / cache between jobs.
- You can have a separate job to POST your artifacts to some remote location / git notes / S3 / gitea

Testing your pipelines too!
---------------------------

Mistakes in the pipeline config can take a long time to catch if you are running a large test harness.

With Jaypore CI it's fairly simple. Just write tests for your pipeline since it's normal Python code!

To help you do this there are mock executors/remotes that you can use instead
of Docker/Gitea. This example taken from Jaypore CI's own tests shows how you
would test and make sure that jobs are running in order.

.. code-block:: python

    from jaypore_ci import jci, executors, remotes

    executor = executors.Mock()
    remote = remotes.Mock(branch="test_branch", sha="fake_sha")
    
    with jci.Pipeline(executor=executor, remote=remote, poll_interval=0) as p:
        for name in "pq":
            p.job(name, name)
        p.job("x", "x")
        p.job("y", "y", depends_on=["x"])
        p.job("z", "z", depends_on=["y"])
        for name in "ab":
            p.job(name, name)

    order = pipeline.executor.get_execution_order()
    # assert order == {}
    assert order["x"] < order["y"] < order["z"]


Contributing
============

- Main development happens on a self hosted gitea instance.
- Source code is mirrored at `Github <https://github.com/theSage21/jaypore_ci>`_
- If you are facing issues please file them on github.
- If you want to open pull requests please open them on github. I'll try to review and merge them when I get time.

Reference
========

.. toctree::
   :glob:

   reference/modules.rst

