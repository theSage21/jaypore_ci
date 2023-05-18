#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


main() {
    export REPO_SHA=$(git rev-parse HEAD)
    export REPO_ROOT=$(git rev-parse --show-toplevel)
    for TARGET in jcienv jcilib jci;
    do
        docker build -t $TARGET --target $TARGET $REPO_ROOT
    done

    docker run \
        -t \
        -e ENV=ci \
        -e REPO_SHA \
        -e REPO_ROOT \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v $REPO_ROOT:/jayporeci/repo:ro \
        -v /tmp/jayporeci__src__$REPO_SHA:/jayporeci/run \
        jci hook
}

(main)
