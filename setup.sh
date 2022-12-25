set -o errexit
set -o nounset
set -o pipefail

main (){
    REPO_ROOT=$(git rev-parse --show-toplevel)
    LOCAL_HOOK=$(echo $REPO_ROOT/.git/hooks/pre-push)
    IMAGE='arjoonn/jci:latest'
    echo "Working in repo: $REPO_ROOT"
    echo "Adding git hook at:  $LOCAL_HOOK"
    CICD_ROOT=cicd
    mkdir $REPO_ROOT/cicd || echo 'Moving on..'
    cat     > $REPO_ROOT/cicd/cicd.py << EOF
from jaypore_ci import jci

with jci.Pipeline() as p:
        p.job("Workingdir", "pwd")
        p.job("Tree", "tree")
        p.job("Black", "black --check .")
        p.job("PyLint", "pylint jaypore_ci/ tests/")
        p.job("PyTest", "pytest tests/")
EOF

    cat     > $REPO_ROOT/cicd/pre-push.sh << EOF
#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


run() {
    export SECRETS_PATH=secrets
    export SECRETS_FILENAME=jaypore_ci
    export \$(SOPS_AGE_KEY_FILE=/jaypore_ci/repo/\$SECRETS_PATH/\$SECRETS_FILENAME.age  sops --decrypt --input-type dotenv --output-type dotenv /jaypore_ci/repo/\$SECRETS_PATH/\$SECRETS_FILENAME.enc | xargs)
    cp -r /jaypore_ci/repo/. /jaypore_ci/run
    cd /jaypore_ci/run/
    git clean -fdx
    # Change the name of the file if this is not cicd.py
    python /jaypore_ci/run/\$JAYPORE_CODE_DIR/cicd.py
}


hook() {
    SHA=\$(git rev-parse HEAD)
    REPO_ROOT=\$(git rev-parse --show-toplevel)
    TOKEN=\$(echo "url=\$(git remote -v|grep push|awk '{print \$2}')"|git credential fill|grep password|awk -F= '{print \$2}')
    JAYPORE_CODE_DIR=\$( cd -- "\$( dirname -- "\${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    JAYPORE_CODE_DIR=\$(basename \$JAYPORE_CODE_DIR)
    # We will mount the current dir into /jaypore_ci/repo
    # Then we will copy things over to /jaypore_ci/run
    # Then we will run git clean to remove anything that is not in git
    # Then we call the actual cicd code
    #
    # We also pass docker.sock to the run so that jaypore_ci can create docker containers
    echo '----------------------------------------------'
    echo "JayporeCi: "
    JAYPORE_GITEA_TOKEN="\${JAYPORE_GITEA_TOKEN:-\$TOKEN}" docker run \\
        -d \\
        --name jaypore_ci_\$SHA \\
        -e JAYPORE_GITEA_TOKEN \\
        -e JAYPORE_CODE_DIR=\$JAYPORE_CODE_DIR \\
        -v /var/run/docker.sock:/var/run/docker.sock \\
        -v \$REPO_ROOT:/jaypore_ci/repo:ro \\
        -v /tmp/jaypore_\$SHA:/jaypore_ci/run \\
        --workdir /jaypore_ci/run \\
        $IMAGE \\
        bash -c "bash /jaypore_ci/repo/\$JAYPORE_CODE_DIR/pre-push.sh run"
    echo '----------------------------------------------'
}
("\$@")
EOF
    echo "Creating git hook for pre-commit"
    chmod u+x $REPO_ROOT/cicd/pre-push.sh

    if test -f "$LOCAL_HOOK"; then
        if test -f "$LOCAL_HOOK.local"; then
            echo "$LOCAL_HOOK has already been moved once."
            echo $LOCAL_HOOK
            echo $LOCAL_HOOK.local
            echo "Please link"
            echo "  Jaypore hook : $REPO_ROOT/cicd/pre-push.sh"
            echo "with"
            echo "  Existing hook: $LOCAL_HOOK"
            echo "manually by editing the existing hook file"
            echo "--------------------------------------"
            echo "Stopping."
            exit 1
        else
            echo "$LOCAL_HOOK exists. Moving to separate file"
            mv $LOCAL_HOOK $REPO_ROOT/.git/hooks/pre-push.local
            echo "$REPO_ROOT/.git/hooks/pre-push.local" >> $REPO_ROOT/.git/hooks/pre-push
        fi
    fi
    echo "$REPO_ROOT/cicd/pre-push.sh" >> $REPO_ROOT/.git/hooks/pre-push
    chmod u+x $LOCAL_HOOK

}
(main)
