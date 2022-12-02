# Jaypore CI

    A CI system that sounds ancient and powerful. Like the city of Jaypore.

## Expected flow

- `curl <link> | base` to install this in any repo.
- Configure CI available at `.jaypore_ci/cicd.py`
- Each git-push will trigger a CI job.
 
## Use cases covered

- Run offline / debug a job
- Run on a cloud machine (more cores/ram /gpu / inside vpn)
- Cache project dependencies in docker 
- Publish images / artifacts to docker / gitea

## What I don't need

- Spending money on CI for small/hobby/idea projects.
- Lose my entire CI system if I move between gitlab / github / gitea / bitbucket.
- Configure/worry about CI access for collaborators every time someone joins the project / leaves.
- To be stuck without CI if I'm offline.
- Trying to figure out how to get X/Y/Z done in the yaml/jsonnet config format for the CI of the day

## Popular solutions that were considered

System              | Cause of rejection
--------------------|-------------
Github actions      | non OSS, money, online only
Gitlab CI           | money, online only, heavy idle consumption
Circle CI           | money, online only
Jenkins             | heavy idle consumption, needs infra setup
Travis CI           | online only
Agola ci            | fragile, needs infra setup
Drone CI            | non OSS, needs infra setup
Woodpecker CI       | needs infra setup


## What do I want?

- Should work offline
- One line install for any project. Something like `curl <link>|bash`
- Zero infra other than docker.
- CI configuration should be a proper programming language. I don't want to learn your custom flavour of yaml/jsonnet etc
- Work with any remote like gitea / github / gitlab / bitbucket / email. Mainly gitea for now since that's what I use.
- Has matrix jobs
- Complex conditional jobs and dependencies
- Needs to be able to run integration tests with services etc
- Easy debugging. I don't want to debug someone else's system.
 
## Installation

1. Make sure you have `docker` installed on your machine.
2. `cd ~/some/path/to/myrepo` You can be anywhere inside your project repo actually.
3. `curl https://github.com/midpath/jaypore_ci | bash`  to install `jaypore_ci` in your repository.
4. `git add -Av && git commit -m 'added jaypore ci' && git push origin`.
    - `Jaypore_ci` will run whenever you push to your remote.

## Examples

```python
from jaypore_ci import jci

with jci.Pipeline(
    image="arjoonn/jaypore_ci:latest",  # NOTE: Change this to whatever you need
    timeout=15 * 60,
) as p:
    p.in_parallel(
        p.job("python3 -m black --check .", name="Black"),
        p.job("python3 -m pylint jaypore_ci/ tests/", name="PyLint"),
        p.job("python3 -m pytest tests/", name="PyTest"),
    ).should_pass()
```
