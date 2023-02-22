#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


run() {
    if [ -z ${ENV+x} ]; then
        echo "ENV : ? -> SKIP sourcing from secrets."
    else
        echo "ENV : '$ENV' -> Sourcing from secrets"
        source /jaypore_ci/repo/secrets/bin/set_env.sh $ENV
    fi
    cp -r /jaypore_ci/repo/. /jaypore_ci/run
    cd /jaypore_ci/run/
    git clean -fdx
    # Change the name of the file if this is not cicd.py
    python /jaypore_ci/run/$JAYPORE_CODE_DIR/cicd.py
}


hook() {
    SHA=$(git rev-parse HEAD)
    REPO_ROOT=$(git rev-parse --show-toplevel)
    JAYPORE_CODE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    JAYPORE_CODE_DIR=$(basename $JAYPORE_CODE_DIR)
    # We will mount the current dir into /jaypore_ci/repo
    # Then we will copy things over to /jaypore_ci/run
    # Then we will run git clean to remove anything that is not in git
    # Then we call the actual cicd code
    #
    # We also pass docker.sock and the docker executable to the run so that
    # jaypore_ci can create docker containers
    echo '----------------------------------------------'
    echo "JayporeCi: "
    docker run \
        -d \
        --name jayporeci__pipe__$SHA \
        -e JAYPORE_CODE_DIR=$JAYPORE_CODE_DIR \
        -e SHA=$SHA \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v $REPO_ROOT:/jaypore_ci/repo:ro \
        -v /tmp/jayporeci__src__$SHA:/jaypore_ci/run \
        --workdir /jaypore_ci/run \
        arjoonn/jci:latest \
        bash -c "ENV=$ENV bash /jaypore_ci/repo/$JAYPORE_CODE_DIR/pre-push.sh run"
    echo '----------------------------------------------'
}
("$@")
