.. Jaypore CI documentation master file, created by
   sphinx-quickstart on Thu Dec 22 13:34:40 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

|logo|
======

- **Jaypore CI** is a *small*, *very flexible*, and *powerful* system for automation within software projects.
- Coverage : |coverage|
- Version  : |package_version| on `PyPi <https://pypi.org/project/jaypore-ci/>`_



TLDR
----

- Configure pipelines in Python
- Jobs are run via docker; on your laptop and on cloud IF needed.
- Send status reports anywhere. Email, Store in git, Gitea PR, Github PR, Telegram, or only on your laptop.


Contents
--------

.. contents::

Getting Started
========

Installation
------------

You can install it using a bash script.

.. code-block:: console

   $ curl https://www.jayporeci.in/setup.sh | bash


**Or** you can manually install it. The names are convention, you can call your
folders/files anything but you'll need to make sure they match everywhere.
    
1. Create a directory called *cicd* in the root of your repo.
2. Create a file *cicd/pre-push.sh*
3. Create a file *cicd/cicd.py*
4. Update your repo's pre-push git hook so that it runs the *cicd/pre-push.sh* file when you push.
    1. Git hook should call `cicd/pre-push.sh`
    2. After setting environment variables `cicd/pre-push.sh` calls
           `cicd/cicd.py` inside a docker container having JayporeCI installed.
           You can use `arjoonn/jci` if you don't have anything else ready.
    3. `cicd/cicd.py` will run your jobs within other docker containers.


Your entire config is inside `cicd/cicd.py`. Edit it to whatever you like! A basic config would look like this:

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline(image='mydocker/image') as p:
        p.job("Black", "black --check .")
        p.job("Pylint", "pylint mycode/ tests/")
        p.job("PyTest", "pytest tests/")

This would produce a CI report like::

    ╔ 🟢 : JayporeCI       [sha edcb193bae]
    ┏━ Pipeline
    ┃
    ┃ 🟢 : Black           [ffcda0a9]   0: 3
    ┃ 🟢 : Pylint          [2417ad58]   0: 9
    ┃ 🟢 : PyTest          [28d4985f]   0:15 [Cov: 65%  ]
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

- **edcb193bae** is the SHA that the report is for.
- **Pipeline** is the default pipeline stage.
- 🟢 indicates that the job has passed
- **Black**, **Pylint**, and **PyTest** are the job names.
- **[ffcda0a9]** is the docker container ID for that job.
- **1: 3** is the time taken by the job.
- **[Cov: 65%  ]** is custom reporting done by the job. Any job can create a file
  **/jaypore_ci/run/<job name>.txt** and the first 5 characters from that file
  will be displayed in the report.
  - Although this is used for coverage reports you could potentially use this for anything you want. A few ideas:
    - You could report error codes here to indicate WHY a job failed.
    - Report information about artifacts created like package publish versions. 


To see the pipelines on your machine you can use a `Dozzle
<https://dozzle.dev/>`_ container on your localhost to explore CI jobs.

If you don't want to do this it's also possible to simply use `docker logs
<container ID>` to explore jobs.


Concepts
--------

1. A pipeline config is simply a python file that imports and uses **jaypore_ci**.
   - It can also import other libraries / configs. Do whatever your usecase needs.
2. A config starts with creating a :class:`~jaypore_ci.jci.Pipeline` instance. Everything happens inside this context.
    - A pipeline has to have one implementation of a
      :class:`~jaypore_ci.interfaces.Remote`,
      :class:`~jaypore_ci.interfaces.Reporter`,
      :class:`~jaypore_ci.interfaces.Executor`, and
      :class:`~jaypore_ci.interfaces.Repo` specified.
    - If you do not specify them then the defaults are
      :class:`~jaypore_ci.remotes.gitea.Gitea`,
      :class:`~jaypore_ci.reporters.text.Text`,
      :class:`~jaypore_ci.executors.docker.Docker`, and
      :class:`~jaypore_ci.repos.git.Git`.
    - You can specify ANY other keyword arguments to the pipeline and they will
      be applied to jobs in that pipeline as a default. This allows you to keep
      your code DRY. For example, we can specify **image='some/docker:image'**
      and this will be used for all jobs in the pipeline.
3. Pipeline components
    1. :class:`~jaypore_ci.interfaces.Repo` holds information about the project.
        - You can use this to get information about things like `sha` and `branch`.
        - Currently only :class:`~jaypore_ci.repos.git.Git` is supported.
    2. :class:`~jaypore_ci.interfaces.Executor` Is used to run the job. Perhaps in
       the future we might have shell / VMs.
    3. :class:`~jaypore_ci.interfaces.Reporter` Given the status of the pipeline
       the reporter is responsible for creating a text output that can be read by
       humans.
       - Along with :class:`~jaypore_ci.reporters.text.Text` , we also have
         the :class:`~jaypore_ci.reporters.markdown.Markdown` reporter that uses
         Mermaid graphs to show you pipeline dependencies.
    4. :class:`~jaypore_ci.interfaces.Remote` is where the report is published to. Currently we have:
        - :class:`~jaypore_ci.remotes.git.GitRemote` which can store the pipeline status
          in git itself. You can then push the status to your github and share it
          with others. This works similar to git-bug.
        - :class:`~jaypore_ci.remotes.gitea.Gitea` can open a PR and publish pipeline status as the PR description on Gitea.
        - :class:`~jaypore_ci.remotes.github.Github` can open a PR and publish pipeline status as the PR description on Github.
        - :class:`~jaypore_ci.remotes.email.Email` can email you the pipeline status.
4. Each pipeline can declare multiple :meth:`~jaypore_ci.jci.Pipeline.stage` sections.
    - Stage names have to be unique. They cannot conflict with job names and other stage names.
    - Stages are executed in the order in which they are declared in the config.
    - The catch all stage is called **Pipeline**. Any job defined outside a stage belongs to this stage.
    - Any extra keyword arguments specified while creating the stage are
      passed to jobs. These arguments override whatever is specified at the
      Pipeline level.
4. Finally, any number of :meth:`~jaypore_ci.jci.Pipeline.job` definitions can be made.
    - Jobs declared inside a stage belong to that stage.
    - Job names have to be unique. They cannot clash with stage names and other job names.
    - Jobs are run in parallel **UNLESS** they specify
      **depends_on=["other_job"]**, in which case the job runs after
      **other_job** has passed.
    - Jobs inherit keyword arguments from Pipelines, then stages, then whatever
      is specified at the job level.

How to
======

See job logs
------------

- The recommended way is to have a `Dozzle <https://dozzle.dev/>`_ container on your localhost to explore CI jobs.
- You can also run `docker logs <container ID>` locally.
- To debug running containers you can `docker exec <container ID>` while the job is running.

Build and publish docker images
-------------------------------

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


Define complex job relations
---------------------

This config builds docker images, runs linting, testing on the
codebase, then builds and publishes documentation.


.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:

        with p.stage("build"):
            p.job("DockDev", f"docker build --target DevEnv -t {p.repo.sha}_dev .")

        with p.stage("checking", image=f"{p.repo.sha}_dev"):
            p.job( "IntTest", "run int_test.sh")
            p.job( "RegText", "bash regression_tests.sh", depends_on=["IntTest"])
            p.job( "FuzzTest", "bash fuzzy_tests.sh", depends_on=["IntTest", "RegText"])


Run a job matrix
----------------
 
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

Run on cloud/remote runners
---------------------------

- Make sure docker is installed on the remote machine.
- Make sure you have ssh access to remote machine and the user you are logging in as can run docker commands.
- Add to your local `~.ssh/config` an entry for your remote machine. Something like:

  .. code-block:: config

    Host my.aws.machine
        HostName some.aws.machine
        IdentityFile ~/.ssh/id_rsa
- Now in your `cicd/pre-push.sh` file, where the `docker run` command is mentioned, simply add `DOCKER_HOST=ssh://my.aws.machine`
- JayporeCi will then run on the remote machine.

Use custom services for testing
-------------------------------

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


Publish Artifacts / Cache
-------------------------

- All jobs run in a shared directory **/jaypore_ci/run**.
- Anything you write to this directory is available to all jobs so you can use this to pass artifacts / cache between jobs.
- You can have a separate job to POST your artifacts to some remote location / git notes / S3 / gitea


Jobs based on files change / branch name
----------------------------------------

Some jobs only need to run when your branch is **main** or in release branches.
At other times we want to check commit messages and based on the message run
different jobs.

.. code-block:: python

    from jaypore_ci import jci

    
    with jci.Pipeline() as p:
        p.job("testing", "bash cicd/lint_test_n_build.sh")
        if p.repo.branch == 'main':
            p.job("publish", "bash cicd/publish_release.sh", depends_on=['testing'])


Test your pipeline config
-------------------------

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
    assert order["x"] < order["y"] < order["z"]

Status report via email
-----------------------

You can send pipeline status reports via email if you don't want to use the PR system for gitea/github etc.

See the :class:`~jaypore_ci.remotes.email.Email` docs for the environment
variables you will have to supply to make this work.

.. code-block:: python

    from jaypore_ci import jci, executors, remotes, repos

    git = repos.Git.from_env()
    email = remotes.Email.from_env(repo=git)
    
    with jci.Pipeline(repo=git, remote=email) as p:
        p.job("x", "x")

Run selected jobs based on commit message
--------------------------------------

Sometimes we want to control when some jobs run. For example, build/release jobs, or intensive testing jobs.
A simple way to do this is to read the commit messsage and see if the author
asked us to run these jobs. JayporeCI itself only runs release jobs when the
commit message contains **jci:release** as one of it's lines.

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline() as p:
        p.job("build", "bash cicd/build.sh")
        if p.repo.commit_message.contains("jci:release"):
            p.job("release", "bash cicd/release.sh", depends_on=["build"])


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

.. |logo| image:: _static/logo80.png
   :width: 80
   :alt: Jaypore CI logo
   :align: middle
