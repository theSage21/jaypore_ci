set -o errexit
set -o nounset
set -o pipefail

main (){
    REPO_ROOT=$(git rev-parse --show-toplevel)
    LOCAL_HOOK=$(echo $REPO_ROOT/.git/hooks/pre-push)
    IMAGE='arjoonn/jaypore_ci:latest'
    echo "Working in repo: $REPO_ROOT"
    mkdir $REPO_ROOT/.jaypore_ci || echo 'Moving on..'
    cat     > $REPO_ROOT/.jaypore_ci/cicd.py << EOF
from jaypore_ci import jci

with jci.Pipeline(
    image="$IMAGE",  # NOTE: Change this to whatever you need
    timeout=15 * 60
) as p:
    p.in_parallel(
        p.job("pwd", name="Pwd"),
        p.job("tree", name="Tree"),
        p.job("python3 -m black --check .", name="Black"),
        p.job("python3 -m pylint jaypore_ci/ tests/", name="PyLint"),
        p.job("python3 -m pytest tests/", name="PyTest"),
    ).should_pass()
EOF

    cat     > $REPO_ROOT/.jaypore_ci/pre-push.githook << EOF
#! /bin/bash
#
set -o errexit
set -o nounset
set -o pipefail


main() {
    SHA=\$(git rev-parse HEAD)
    REPO_ROOT=\$(git rev-parse --show-toplevel)
    TOKEN=\$(echo "url=\$(git remote -v|grep push|awk '{print \$2}')"|git credential fill|grep password|awk -F= '{print \$2}')
    # We will mount the current dir into /jaypore/repo
    # Then we will copy things over to /jaypore/run
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
        -v /var/run/docker.sock:/var/run/docker.sock \\
        -v \$REPO_ROOT:/jaypore/repo:ro \\
        -v /tmp/jaypore_\$SHA:/jaypore/run \\
        --workdir /jaypore/run \\
        $IMAGE \\
        bash -c 'cp -r /jaypore/repo/. /jaypore/run && cd /jaypore/run/ && git clean -fdx && python .jaypore_ci/cicd.py'
    echo '----------------------------------------------'
}
(main)
EOF
    echo "Creating git hook for pre-commit"
    chmod u+x $REPO_ROOT/.jaypore_ci/pre-push.githook

    if test -f "$LOCAL_HOOK"; then
        if test -f "$LOCAL_HOOK.local"; then
            echo "$LOCAL_HOOK has already been moved once."
            echo $LOCAL_HOOK
            echo $LOCAL_HOOK.local
            echo "Please link"
            echo "  Jaypore hook : $REPO_ROOT/.jaypore_ci/pre-push.githook"
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
    echo "$REPO_ROOT/.jaypore_ci/pre-push.githook" >> $REPO_ROOT/.git/hooks/pre-push
    chmod u+x $LOCAL_HOOK

}
(main)
