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
    p.job("Black", "black --check .")
EOF

    curl https://raw.githubusercontent.com/theSage21/jaypore_ci/main/cicd/pre-push.sh -o $REPO_ROOT/cicd/pre-push.sh
    # --------------
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
    echo "$REPO_ROOT/cicd/pre-push.sh hook" >> $REPO_ROOT/.git/hooks/pre-push
    chmod u+x $LOCAL_HOOK

}
(main)
