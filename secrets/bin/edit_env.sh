#!/usr/bin/env bash

set -o errexit
set -o pipefail

main (){
    NAME=$1
    BIN=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    SECRETS=$(echo "$BIN/..")
    KEY_FILE=$(echo "$SECRETS/$NAME.key")
    ENC_FILE=$(echo "$SECRETS/$NAME.enc")
    PLAINTEXT_FILE=$(echo "$SECRETS/$NAME.plaintext")
    echo $BIN
    echo $SECRETS
    echo $KEY_FILE
    echo $ENC_FILE
    echo $PLAINTEXT_FILE
    if [[ -f "$SECRETS/$NAME.enc" ]]; then
        SOPS_AGE_KEY_FILE=$KEY_FILE $BIN/sops --decrypt --input-type dotenv --output-type dotenv $ENC_FILE > $PLAINTEXT_FILE
    fi
    vim $PLAINTEXT_FILE
    $BIN/sops --input-type dotenv --output-type dotenv --encrypt --age $($BIN/age-keygen -y $KEY_FILE) $PLAINTEXT_FILE > $ENC_FILE
    rm $PLAINTEXT_FILE
}
(main $1)
