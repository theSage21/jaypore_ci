#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


run() {
    if [ -z ${ENV+x} ]; then
        echo "ENV : ? -> SKIP sourcing from secrets."
    else
        echo "ENV : '$ENV' -> Sourcing from secrets"
        echo "---"
        source /jaypore_ci/repo/secrets/bin/set_env.sh $ENV
    fi
    cp -r /jaypore_ci/repo/. /jaypore_ci/run
    cd /jaypore_ci/run/
    git clean -fdx
    # Change the name of the file if this is not cicd.py
    echo "---- Container ID:"
    cat /jaypore_ci/cidfiles/$SHA
    echo
    echo "---- ======="
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
    mkdir -p /tmp/jayporeci__cidfiles &> /dev/null
    echo '----------------------------------------------'
    echo "Jaypore CI"
    echo "Building image    : "
    docker build \
        --build-arg JAYPORECI_VERSION=$EXPECTED_JAYPORECI_VERSION \
        -t im_jayporeci__pipe__$SHA \
        -f $REPO_ROOT/$JAYPORE_CODE_DIR/Dockerfile \
        $REPO_ROOT
    echo "Running container : "
    docker run \
        -d \
        --name jayporeci__pipe__$SHA \
        -e JAYPORE_CODE_DIR=$JAYPORE_CODE_DIR \
        -e SHA=$SHA \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v /tmp/jayporeci__src__$SHA:/jaypore_ci/run \
        -v /tmp/jayporeci__cidfiles:/jaypore_ci/cidfiles:ro \
        --cidfile /tmp/jayporeci__cidfiles/$SHA \
        --workdir /jaypore_ci/run \
        im_jayporeci__pipe__$SHA \
        bash -c "ENV=$ENV bash /jaypore_ci/repo/$JAYPORE_CODE_DIR/pre-push.sh run"
    echo '----------------------------------------------'
}
EXPECTED_JAYPORECI_VERSION=latest

# --------- runner
("$@")
