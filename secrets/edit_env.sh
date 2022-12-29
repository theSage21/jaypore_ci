#!/usr/bin/env bash

set -o errexit
set -o pipefail

main (){
    NAME=$1
    SOPS_AGE_KEY_FILE=secrets/$NAME.age sops --decrypt --input-type dotenv --output-type dotenv secrets/$NAME.enc > secrets/$NAME.env
    vim secrets/$NAME.env
    sops --encrypt --age $(age-keygen -y secrets/$NAME.age) secrets/$NAME.env > secrets/$NAME.enc
    rm secrets/$NAME.env
}

help_message (){

    echo "
    Easily edit env files.
    Make sure you have age keys available in

        ~/.ssh/smaac/agekeys/<envname>.txt

    If that is available you can run the following to edit env files.

        ./api/bin/edit_env.sh <envname>

    Upon exiting the editor the file will be re-encrypted.
    "
}

if [[ $1 == "--help" || $1 == "-h" ]]; then
    help_message
    exit 0
fi
if [ -z $1 ]; then
    help_message
    exit 0
fi
(main $1)
