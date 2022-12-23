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
        p.job("PyTest", "pytest tests/")


Go through the :doc:`getting_started` doc to set up your first instance.


Contents
---------------

.. toctree::
   :glob:

   getting_started
   ideas
   examples
   reference/modules.rst
