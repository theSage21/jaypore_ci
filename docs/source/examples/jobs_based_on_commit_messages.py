from jaypore_ci import jci

with jci.Pipeline() as p:
    p.job("build", "bash cicd/build.sh")

    # The job only gets defined when the commit message contains 'jci:release'
    if "jci:release" in p.repo.commit_message:
        p.job("release", "bash cicd/release.sh", depends_on=["build"])
