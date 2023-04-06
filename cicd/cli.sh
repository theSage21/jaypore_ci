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

__build__(){
    echo '----------------------------------------------'
    echo "Jaypore CI"
    echo "Building image    : "
    docker build \
        --build-arg JAYPORECI_VERSION=$EXPECTED_JAYPORECI_VERSION \
        -t im_jayporeci__pipe__$SHA \
        -f $REPO_ROOT/cicd/Dockerfile \
        $REPO_ROOT
}


hook() {
    __build__
    mkdir -p /tmp/jayporeci__cidfiles &> /dev/null
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
        bash -c "ENV=$ENV bash /jaypore_ci/repo/$JAYPORE_CODE_DIR/cli.sh run"
    echo '----------------------------------------------'
}


activate(){
    echo "Which environment would you like to use?"
    echo "Keys are available for:"
    for env in $REPO_ROOT/secrets/*key;
    do
        echo "    - " $(basename $env | awk -F\. '{print $1}')
    done
    echo "Available environments are:"
    for env in $REPO_ROOT/secrets/*enc;
    do
        echo "    - " $(basename $env | awk -F\. '{print $1}')
    done
    echo "---------"
    read -r -p "Enter env name to use: " response
    echo $response
    if test -f "$REPO_ROOT/.git/hooks/pre-push"; then
        echo "$REPO_ROOT/.git/hooks/pre-push already exists. Please add the following line to the file manually."
        echo ""
        echo "ENV=$response $REPO_ROOT/cicd/cli.sh hook"
    else
        echo "ENV=$response $REPO_ROOT/cicd/cli.sh hook" > $REPO_ROOT/.git/hooks/pre-push
        chmod u+x $REPO_ROOT/.git/hooks/pre-push
    fi
}

helptext(){
    echo "
    Jaypore CI: cli.sh
    =======================

    This cli.sh script has a few functions that can be used to run Jaypore CI.
    You can use it like:

        $ bash cicd/cli.sh <cmd>

    The available commands are as follows:

        hook
        ----

            $ bash cicd/cli.sh hook

        This command is usually put inside the '.git/hooks/pre-push' file
        and is used to indicate that the pre-push hook has been triggered.
        It will create a docker container and run Jaypore CI inside that.

        run
        ---

            $ bash cicd/cli.sh run

        This command runs the actual 'cicd/cicd.py' file using python. It is
        usually automatically invoked inside the docker container created by
        the 'hook' command.

        activate
        --------

        When we clone a new repo, Jaypore CI is already available in it but the
        pre-push hooks are not established. This command will establish the
        hook for the repo.

        helptext
        --------

            $ bash cicd/cli.sh helptext
            $ bash cicd/cli.sh

        Show this help document and exit. If no command is specified this
        command is the default one.
    "
}

EXPECTED_JAYPORECI_VERSION=latest
echo "EXPECTED_JAYPORECI_VERSION : $EXPECTED_JAYPORECI_VERSION"
if [ -z ${REPO_ROOT+x} ]; then
    echo "REPO_ROOT : Not found"
    echo "Stopping"
    exit 1
else
    echo "REPO_ROOT : $REPO_ROOT"
fi
CMD="${@:-helptext}" 
echo "CMD : $CMD"
echo "-------"

# --------- runner
("$CMD")
