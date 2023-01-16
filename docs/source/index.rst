.. Jaypore CI documentation master file, created by
   sphinx-quickstart on Thu Dec 22 13:34:40 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Jaypore CI's documentation!
======================================

**Jaypore CI** is a small system for continuous integration / testing / delivery.

It is different from the usual suspects like github actions, gitlab CI, drone CI and so on.

- The configuration language is python.
- CI runs on your local machine by default. 
- There is no "server". You can run offline.


For example, here's a CI pipeline for a project.

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline(image='mydockerhub/env_image') as p:
        p.job("Black", "black --check .")
        p.job("Pylint", "pylint mycode/ tests/")
        p.job("PyTest", "pytest tests/", depends_on=["Black", "Pylint"])


Getting Started
===============

Installation
------------


To use **Jaypore CI**, first install it using a bash script.

.. code-block:: console

   $ curl https://get.jayporeci.in | bash


Doing this will:
    
1. Create a directory called `cicd` in the root of your repo.
2. Create a file `cicd/pre-push.sh`
3. Create a file `cicd/cicd.py`
4. Update your repo's pre-push git hook so that it runs the `cicd/pre-push.sh` file when you push.


Basic config
------------

Your entire config is inside `cicd/cicd.py`. Edit it to whatever you like! A basic config would look like this:

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline(image='mydocker/image') as p:
        p.job("Black", "black --check .")
        p.job("Pylint", "pylint mycode/ tests/")
        p.job("PyTest", "pytest tests/")


After you make these changes you can `git add -Av` and `git commit -m 'added Jaypore CI'`.

When you do a `git push origin`, that's when the CI system will get triggered and will run the CI.

This config will run three jobs in parallel, using the `mydocker/image` docker image.

See :doc:`examples` for more complex examples and :doc:`ideas` for understanding how it works.


Contents
--------

.. toctree::
   :glob:

   ideas
   examples
   reference/modules.rst
