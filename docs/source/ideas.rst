Ideas
=====

I'm tired of
------------

- Spending hours figuring out how to do stuff in YAML configs.
- Shift to something else when pricing changes.
- Debugging why stuff is not working only in the CI system.
- Not being able to run CI without internet.
- In the case of self CI runners hosted on laptops, I don't want my laptop bogged down by jobs that other people pushed.


What I like about existing systems
----------------------------------

- Use docker to run things.
- Stateless job runs.
- Job graphs showing status of the run.
- We cannot merge PRs unless the pipeline passes.
- Able to handle multiple languages easily in the same project.


Concepts used
-------------

- We use a git hook as a trigger mechanism. There is no possibility that some "CI server" is down.
- Jobs are run on the machine that pushed the job by default. If you write bad code, your machine suffers first.
- CI run status is posted directly in the PR description. You don't have to click and reach another website to see what your job is doing.
- All jobs run inside docker containers.
