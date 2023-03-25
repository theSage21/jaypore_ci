from jaypore_ci import jci


with jci.Pipeline() as p:
    p.job("testing", "bash cicd/lint_test_n_build.sh")
    # This job will only be defined when the branch is main. Otherwise it will
    # not be a part of the pipeline
    if p.repo.branch == "main":
        p.job(
            "publish",
            "bash cicd/publish_release.sh",
            depends_on=["testing"],
        )
    # The following job will only be run when documentation changes.
    if any(path.startswith("docs") for path in p.repo.files_changed("develop")):
        p.job(
            "build_docs",
            "bash cicd/build_docs.sh",
            depends_on=["testing"],
        )
