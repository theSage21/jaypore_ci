#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


main() {
    mkdir /fake_py_repo
    JCI_ROOT=$PWD
    cd /fake_py_repo
    echo "
print(1
+
1)" > code.py
    git config --global user.email "fake@email.com"
    git config --global user.name "Fake User"
    git config --global init.defaultBranch develop
    git init
    git add -Av
    git commit -m 'init'
    export RUNNING_IN_CI=yes
    bash $JCI_ROOT/setup.sh -y
    git add -Av
    git commit -m 'installed Jci'
}

(main)
