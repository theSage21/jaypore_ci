set -o errexit
set -o nounset
set -o pipefail

RUNNING_IN_CI="${RUNNING_IN_CI:-no}"
ASSUME_YES="no"
while getopts ":y" opt; do
  case $opt in
    y)
      ASSUME_YES="yes"
      ;;
  esac
done

echo "RUNNING_IN_CI : $RUNNING_IN_CI"
echo "ASSUME_YES    : $ASSUME_YES"

should_continue (){
    if [[ "$ASSUME_YES" = "yes" ]]
    then
        return 0
    fi
    # ---
    read -r -p "Continue? [Y/n] " response
    if [[ "$response" = "" ]]
    then
        return 0
    fi
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
    then
        return 0
    fi
    return 1
}

getfile(){
    if [ "$RUNNING_IN_CI" = "yes" ]; then
        ROOT='/jaypore_ci/run'
        SOURCE=$(echo "$ROOT$1")
        if [ -f "$ROOT/cicd$1" ]; then
            SOURCE=$(echo "$ROOT/cicd$1")
        fi
        if [ -f "$ROOT/secrets$1" ]; then
            SOURCE=$(echo "$ROOT/secrets$1")
        fi
        echo "Getting file: $SOURCE $2"
        cp $SOURCE $2
    else
        wget --quiet -O $2 https://www.jayporeci.in$1
    fi
}

main (){
    REPO_ROOT=$(git rev-parse --show-toplevel)
    LOCAL_HOOK=$(echo $REPO_ROOT/.git/hooks/pre-push)
    CICD_ROOT=cicd
    echo "--------------------"
    echo "Installing JayporeCI"
    echo "--------------------"
    echo "Installing in repo: $REPO_ROOT"
    echo "Creating folder for cicd:  $REPO_ROOT/$CICD_ROOT"
    # ----------------==
    if should_continue;
    then
        echo "Creating cicd.py and pre-push.sh"
    else
        exit 0
    fi
    mkdir $REPO_ROOT/$CICD_ROOT || echo 'Moving on..'
    cat     > $REPO_ROOT/$CICD_ROOT/cicd.py << EOF
from jaypore_ci import jci

with jci.Pipeline() as p:
    p.job("Black", "black --check .")
EOF
    getfile /pre-push.sh $REPO_ROOT/cicd/pre-push.sh
    getfile /Dockerfile $REPO_ROOT/cicd/Dockerfile
    chmod u+x $REPO_ROOT/cicd/pre-push.sh
    # ----------------==
    ENV_PREFIX=''
    echo "Creating 'secrets' folder for environment variables."
    if should_continue
    then
        mkdir -p secrets/bin
        PATH="$REPO_ROOT/secrets/bin:$PATH"
        BINLOC=$HOME/.local/jayporeci_bin
        echo "Downloading age/sops binaries to: $BINLOC"
        if should_continue
        then
            echo "Downloading age/ binaries"
            mkdir -p $BINLOC &> /dev/null
            getfile /bin/age $BINLOC/age &
            getfile /bin/age-keygen $BINLOC/age-keygen &
            getfile /bin/sops $BINLOC/sops &
            wait
            chmod u+x $BINLOC/age $BINLOC/age-keygen $BINLOC/sops
        fi
        echo "Adding line to .bashrc:"
        echo "  \$PATH=$BINLOC:\$PATH"
        if should_continue
        then
            echo "export PATH=$BINLOC:\$PATH" >> $HOME/.bashrc
            source $HOME/.bashrc
        fi
        echo "Downloading edit/set env scripts"
        getfile /bin/edit_env.sh secrets/bin/edit_env.sh  &
        getfile /bin/set_env.sh secrets/bin/set_env.sh &
        wait
        echo "Created $REPO_ROOT/secrets/bin"
        echo "Adding gitignore so that key and plaintext files are never committed"
        echo "*.key" >> .gitignore
        echo "*.plaintext" >> .gitignore
        echo "Creating new age-key at: $REPO_ROOT/secrets/ci.key"
        age-keygen > $REPO_ROOT/secrets/ci.key
        echo "You can now use (bash secrets/bin/edit_env.sh ci) to edit environment variables."
        echo "Editing secrets now"
        if [ "$RUNNING_IN_CI" = "yes" ]; then
            echo "Skip setting env file. Running in CI"
        else
            if should_continue
            then
                (bash $REPO_ROOT/secrets/bin/edit_env.sh ci)
            fi
        fi
        ENV_PREFIX='ENV=ci '
    fi
    # ----------------==
    echo "Creating git hook for pre-push"
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
            mv $LOCAL_HOOK $REPO_ROOT/.git/hooks/pre-push.old
            echo "$REPO_ROOT/.git/hooks/pre-push.old" >> $REPO_ROOT/.git/hooks/pre-push
        fi
    fi
    echo "$ENV_PREFIX$REPO_ROOT/cicd/pre-push.sh hook" >> $REPO_ROOT/.git/hooks/pre-push
    chmod u+x $LOCAL_HOOK
}
(main)
