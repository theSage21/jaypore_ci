from jaypore_ci import jci, repos, remotes

repo = repos.Git.from_env()
# Specify JAYPORE_GITHUB_TOKEN in your secrets file
remote = remotes.Github.from_env(repo=repo)

with jci.Pipeline(repo=repo, remote=remote) as p:
    p.job("Pytest", "pytest ")
