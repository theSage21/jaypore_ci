from jaypore_ci.config import Version

V = Version.parse
version_map = {
    V("0.2.28"): {
        "changes": [
            (
                "Bugfix: When there are multiple (push) remotes, Jaypore CI"
                " will pick the first one and use that"
            )
        ],
        "instructions": [],
    },
    V("0.2.27"): {
        "changes": [
            "Jobs older than 1 week will be removed before starting a new pipeline."
        ],
        "instructions": [],
    },
    V("0.2.26"): {
        "changes": [
            (
                "The Dockerfile inside `cicd/Dockerfile` now requires a build arg "
                "that specifies the version of Jaypore CI to install."
            ),
        ],
        "instructions": [
            "Please run the Jaypore CI setup once again.",
        ],
    },
    V("0.2.25"): {
        "changes": [
            (
                "A dockerfile is now used to send context of the codebase to "
                "the docker daemon instead of directly mounting the code."
            )
        ],
        "instructions": [],
    },
}
