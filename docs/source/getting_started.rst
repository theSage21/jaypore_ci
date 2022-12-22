Getting Started
===============

Installation
------------


To use Jaypore CI, first install it using the bash script for installation:

.. code-block:: console

   $ curl https://raw.githubusercontent.com/theSage21/jaypore_ci/main/setup.sh | bash


This will
    
1. Create a directory called `cicd` in the root of your repo.
2. Create a file `cicd/pre-push.githook`
3. Create a file `cicd/cicd.py`
4. Update your repo's pre-push git hook so that it runs the `cicd/pre-push.githook` file when you push.


How it works
------------

1. Every time you run `git push`, the `cicd/pre-push.githook` is run.
    1. This hook runs your `cicd/cicd.py` file using the `arjoonn/jaypore_ci:latest` docker container.
    2. The run has access to your local docker instance and so can launch other containers.


A Basic Config
--------------

Your entire config is inside `cicd/cicd.py`. Edit it to whatever you like! A simple config would look like this:

.. code-block:: python

    from jaypore_ci import jci

    with jci.Pipeline(image='mydocker/image') as p:
        p.job("Black", "python3 -m black --check .")
        p.job("Pylint", "python3 -m pylint mycode/ tests/")
        p.job("PyTest", "python3 -m pytest tests/")


This config will run three jobs in parallel, using the `mydocker/image` docker image.

See :doc:`examples` for more complex examples and :doc:`ideas` for understanding how it works.
