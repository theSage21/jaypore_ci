.. Jaypore CI documentation master file, created by
   sphinx-quickstart on Thu Dec 22 13:34:40 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

TLDR
====

|logo|

- **Jaypore CI** is a *small*, *very flexible*, and *powerful* system for automation within software projects.
- Latest version: |package_version|
- `Test coverage </htmlcov>`_ : |coverage|
- `PyPi <https://pypi.org/project/jaypore-ci/>`_ 
- `Docker Hub <https://hub.docker.com/r/arjoonn/jci>`_
- `Github Mirror <https://github.com/theSage21/jaypore_ci>`_

------------

- Configure pipelines in Python
- Jobs are run using `Docker <https://www.docker.com/>`_; on your laptop and on cloud IF needed.
- Send status reports anywhere, or nowhere at all. Email, commit to git, Gitea
  PR, Github PR, or write your own class and send it where you want.


Getting Started
===============

Installation
------------

You can install Jaypore CI using a bash script. The script only makes changes in your
repository so if you want you can do the installation manually as well.

.. code-block:: console

   $ cd ~/myrepository
   $ curl https://www.jayporeci.in/setup.sh > setup.sh
   $ bash setup.sh -y


**For a manual install** you can do the following. The names are convention,
you can call your folders/files anything but you'll need to make sure they
match everywhere.
    
1. Create a file *cicd/config/main.py* in your repo.
2. Add the activation command to your *.git/hooks/pre-push* file.


Your entire config is inside `cicd/config/main.py`. Edit it to whatever you like! A basic config would look like this:

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
- **[Cov: 65%  ]** is custom reporting done by the job.
  - Any job can create a file **/jaypore_ci/run/<job name>.txt** and the first 5 characters from that file will be displayed in the report.
  - Although this is used for coverage reports you could potentially use this for anything you want.
  - You could report error codes here to indicate WHY a job failed.
  - Report information about artifacts created like package publish versions. 


To see the pipelines on your machine you can use a `Dozzle
<https://dozzle.dev/>`_ container on your localhost to explore CI jobs.

If you don't want to do this it's also possible to simply use `docker logs
<container ID>` to explore jobs.


Concepts
--------

Pipeline config
***************

.. mermaid::

    sequenceDiagram
        autonumber
        loop Pipeline execution
            Pipeline ->> Executor: docker run [n jobs]
            Executor -->> Pipeline: docker inspect [k jobs]
            Pipeline ->> Reporter: Pipeline status
            Reporter -->> Pipeline: Rendered report
            Pipeline ->> Remote: Publish report
            Remote -->> Pipeline: ok
        end

1. A pipeline is defined inside a python file that imports and uses **jaypore_ci**.
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
3. Parts of a pipeline
    1. :class:`~jaypore_ci.interfaces.Repo` holds information about the project.
        - You can use this to get information about things like `sha` and `branch`.
        - It can also tell you which files have changed using
          :meth:`~jaypore_ci.interfaces.Repo.files_changed`.
        - Currently only :class:`~jaypore_ci.repos.git.Git` is supported.
    2. :class:`~jaypore_ci.interfaces.Executor` Is used to run the job. Perhaps in
       the future we might have shell / VMs.
    3. :class:`~jaypore_ci.interfaces.Reporter` Given the status of the pipeline
       the reporter is responsible for creating a text output that can be read by
       humans.
       Along with :class:`~jaypore_ci.reporters.text.Text` , we also have
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
5. Finally, any number of :meth:`~jaypore_ci.jci.Pipeline.job` definitions can be made.
    - Jobs declared inside a stage belong to that stage.
    - Job names have to be unique. They cannot clash with stage names and other job names.
    - Jobs are run in parallel **UNLESS** they specify
      **depends_on=["other_job"]**, in which case the job runs after
      **other_job** has passed.
    - Jobs inherit keyword arguments from Pipelines, then stages, then whatever
      is specified at the job level.


Secrets and environment variables
*********************************

1. JayporeCI uses `SOPS <https://github.com/mozilla/sops>`_ to manage environment variables and secrets.
    - We add `secrets/<env_name>.enc` to store secrets.
    - We add `secrets/<env_name>.key` to decrypt corresponding secret files. This is an `AGE <https://github.com/FiloSottile/age>`_ key file. **Do NOT commit this to git!**. JayporeCI automatically adds a gitignore to ignore key files.
    - We also add `secrets/bin/edit_env.sh` and `secrets/bin/set_env.sh` to help you manage your secrets easily.
2. It is a good idea to have separate secret files for each developer, each environment respectively.
    - For example, JayporeCI itself only has a single secret file called `ci`.


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

.. literalinclude:: examples/build_and_publish_docker_images.py
  :language: python
  :linenos:

Define complex job relations
----------------------------

This config builds docker images, runs linting, testing on the
codebase, then builds and publishes documentation.

.. literalinclude:: examples/complex_dependencies.py
  :language: python
  :linenos:


Run a job matrix
----------------
 
There is no special concept for matrix jobs. Just declare as many jobs as you
want in a while loop. There is a function to make this easier when you want to
run combinations of variables.

.. literalinclude:: examples/job_matrix.py
  :language: python
  :linenos:


The above config generates 3 x 3 x 2 = 18 jobs and sets the environment for each to a unique combination of `BROWSER` , `SCREENSIZE`, and `ONLINE`.

Run on cloud/remote runners
---------------------------

- Make sure docker is installed on the remote machine.
- Make sure you have ssh access to remote machine and the user you are logging in as can run docker commands.
- Add to your local `~.ssh/config` an entry for your remote machine. Something like:

  .. code-block:: text

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



.. literalinclude:: examples/custom_services.py
  :language: python
  :linenos:


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

.. literalinclude:: examples/optional_jobs.py
  :language: python
  :linenos:


Test your pipeline config
-------------------------

Mistakes in the pipeline config can take a long time to catch if you are running a large test harness.

With Jaypore CI it's fairly simple. Just write tests for your pipeline since it's normal Python code!

To help you do this there are mock executors/remotes that you can use instead
of Docker/Gitea. This example taken from Jaypore CI's own tests shows how you
would test and make sure that jobs are running in order.

.. literalinclude:: examples/optional_jobs.py
  :language: python
  :linenos:

Status report via email
-----------------------

You can send pipeline status reports via email if you don't want to use the PR system for gitea/github etc.

See the :class:`~jaypore_ci.remotes.email.Email` docs for the environment
variables you will have to supply to make this work.


.. literalinclude:: examples/report_via_email.py
  :language: python
  :linenos:

Run selected jobs based on commit message
-----------------------------------------

Sometimes we want to control when some jobs run. For example, build/release jobs, or intensive testing jobs.
A simple way to do this is to read the commit messsage and see if the author
asked us to run these jobs. JayporeCI itself only runs release jobs when the
commit message contains **jci:release** as one of it's lines.


.. literalinclude:: examples/jobs_based_on_commit_messages.py
  :language: python
  :linenos:

`💬 <https://github.com/theSage21/jaypore_ci/discussions/20>`_ :Select remote based on job status / branch / authors
--------------------------------------------------------------------------------------------------------------------

.. note::
   If you want this feature please go and vote for it on the `github discussion
   <https://github.com/theSage21/jaypore_ci/discussions>`_.

At times it's necessary to inform multiple people about CI failues / passing.

For example

- Stakeholders might need notifications when releases happen.
- People who wrote code might need notifications when their code breaks on a more intensite test suite / fuzzying run.
- Perhaps you have downstream codebases that need to get patched when you do bugfixes.
- Or perhaps a failure in the build section of the pipeline needs one set of
  people to be informed and a failure in the user documentation building needs
  another set of people.


While all of this is already possible with JayporeCI, if this is a common
workflow you can vote on it and we can implement an easier way to declare this
configuration.

Run multiple pipelines on every commit
--------------------------------------

You can modify `cicd/pre-push.sh` so that instead of creating a single pipeline
it creates multiple pipelines. This can be useful when you have a personal CI
config that you want to run and a separate team / organization pipeline that
needs to be run as well.

This is not the recommended way however since it would be a lot easier to make
`cicd/cicd.py` a proper python package instead and put the two configs there
itself.

Passing extra_hosts and other arguments to docker
-------------------------------------------------

Often times you want to configure some extra stuff for the docker run command
that will be used to run your job, like when you want to pass `extra_hosts` or
`device_requests` to the container.

To do such things you can use the `executor_kwargs` argument while defining the
job using :meth:`~jaypore_ci.jci.Pipeline.job`. Anything that you pass to
this dictionary will be handed off to `Docker-py
<https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run>`_
and so you can use anything that is mentioned in that documentation.

.. literalinclude:: examples/extra_hosts.py
  :language: python
  :linenos:

Using a github remote
---------------------

If you want to use github instead of gitea, it's very simple to use.

.. literalinclude:: examples/github_remote.py
  :language: python
  :linenos:

Multiple pipelines
------------------

You might want to run parallel pipelines for independent things. For example,
one pipeline can run the build-lint-test-release jobs with complex dependencies
and another pipeline can start notifying the correct people to review the PR /
start manual actions needed to do a release etc.

To have multiple pipelines you would create multiple python files inside the
*cicd/config* folder. All pipelines will be run in parallel.


Contributing
============

- Development happens on a self hosted gitea instance and the source code is mirrored at `Github <https://github.com/theSage21/jaypore_ci>`_.
- If you are facing issues please file them on github.
- Please use `Github discussions <https://github.com/theSage21/jaypore_ci/discussions>`_ for describing problems / asking for help / adding ideas.
- Jaypore CI is open source, but not openly developed yet so instead of submitting PRs, please fork the project and start a discussion.

Reference
=========

.. toctree::
   :glob:

   reference/modules.rst

.. |logo| image:: _static/logo80.png
   :width: 80
   :alt: Jaypore CI
   :align: middle

Changelog
=========

