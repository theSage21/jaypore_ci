#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


# TODO: We have to update TUI so that it reads job logs from git instead of just docker.
# TODO: JCI logging should commit things to git after it is complete.
# TODO: JCI should offer capability to git-push/fetch job logs.

main(){
    SHA=e827f9a0a6 
    rm /tmp/tree.txt || echo "No such file exists"

    # Run through a list of docker container IDs and names
    for PAIR in "b6326575 JayporeCI" "200c5b71 JciEnv" "021ffe61 Jci" "f9f3b7b4 black" "66497172 pylint" "6bc7eb99 pytest" "11fb552c DockerHubJci" "f1cbbd4b DockerHubJcienv" "e99ec6e0 PublishDocs" "57cf28ee PublishPypi"
    do
        set -- $PAIR
        CID=$1
        NAME=$2
        # --- Create blobs from the logs
        GIT_BLOB_SHA=$(docker logs $CID 2>&1 | git hash-object -w --stdin)
        echo $GIT_BLOB_SHA $NAME
        # Accumulate them to a file to create a tree later on
        echo -e "100644 blob $GIT_BLOB_SHA\t$NAME.txt" >> /tmp/tree.txt
    done

    # Create a tree
    GIT_TREE_SHA=$(cat /tmp/tree.txt | git mktree)
    echo "GIT_WRITE_TREE: $GIT_TREE_SHA"

    # Commit that tree
    # TODO: This part requires us to set identity. How should we handle this? :thinking:
    GIT_COMMIT_SHA=$(echo 'Jaypore CI logs' | git commit-tree $GIT_TREE_SHA)
    echo "COMMIT_SHA: $GIT_COMMIT_SHA"

    # Update the refs so that the provided SHA will point to this tree
    git update-ref refs/jayporeci/$SHA $GIT_COMMIT_SHA
    git push origin refs/jayporeci/*:refs/jayporeci/*
    git fetch origin refs/jayporeci/*:refs/jayporeci/*
}

(main)
