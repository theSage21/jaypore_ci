from jaypore_ci import jci, executors, remotes, repos

git = repos.Git.from_env()
email = remotes.Email.from_env(repo=git)

# The report for this pipeline will go via email.
with jci.Pipeline(repo=git, remote=email) as p:
    p.job("hello", "bash -c 'echo hello'")
