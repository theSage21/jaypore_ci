from jaypore_ci.config import Version

V = Version.parse
NEW = "🎁"
CHANGE = "⚙️"
BUGFIX = "🐞"

version_map = {
    V("0.2.30"): {
        "changes": [
            (
                f"{NEW}: You can pass arbitrary arguments to the `docker run` "
                "command simply by using the `executor_kwargs` argument while "
                "defining the job. Read more in `Passing extra_hosts and other "
                "arguments to docker`_."
            ),
            f"{NEW}: SSH remotes are now compatible with Jaypore CI.",
        ],
        "instructions": [],
    },
    V("0.2.29"): {
        "changes": [
            (
                f"{BUGFIX}: When gitea token does not have enough scope log"
                " correctly and exit"
            )
        ],
        "instructions": [],
    },
    V("0.2.28"): {
        "changes": [
            (
                f"{BUGFIX}: When there are multiple (push) remotes, Jaypore CI"
                " will pick the first one and use that."
            )
        ],
        "instructions": [],
    },
    V("0.2.27"): {
        "changes": [
            (
                f"{NEW}: Jobs older than 1 week will be removed before starting"
                " a new pipeline."
            )
        ],
        "instructions": [],
    },
    V("0.2.26"): {
        "changes": [
            (
                f"{CHANGE}: The Dockerfile inside `cicd/Dockerfile` now"
                " requires a build arg that specifies the version of Jaypore CI"
                " to install."
            ),
        ],
        "instructions": [
            "Please run the Jaypore CI setup once again.",
        ],
    },
    V("0.2.25"): {
        "changes": [
            (
                f"{NEW}: A dockerfile is now used to send context of the"
                " codebase to the docker daemon instead of directly mounting the"
                " code. This allows us to easily use remote systems for jobs"
            )
        ],
        "instructions": [],
    },
}
assert all(
    line.startswith(NEW) or line.startswith(CHANGE) or line.startswith(BUGFIX)
    for log in version_map.values()
    for line in log["changes"]
), "All change lines must start with one of NEW/CHANGE/BUGFIX"
