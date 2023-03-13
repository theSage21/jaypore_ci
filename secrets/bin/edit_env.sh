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
    export SOPS_AGE_KEY_FILE=$KEY_FILE
    echo "BIN      = $BIN"
    echo "SECRETS  = $SECRETS"
    echo "KEY      = $KEY_FILE"
    echo "SOPS KEY = $SOPS_AGE_KEY_FILE"
    echo "ENC      = $ENC_FILE"
    echo "PLAIN    = $PLAINTEXT_FILE"
    PATH="$BIN:$PATH"
    if [[ -f "$ENC_FILE" ]]; then
        sops --decrypt --input-type dotenv --output-type dotenv "$ENC_FILE" > "$PLAINTEXT_FILE"
    fi
    ${EDITOR:-nano} "$PLAINTEXT_FILE"
    sops --input-type dotenv --output-type dotenv --encrypt --age $(age-keygen -y "$KEY_FILE") "$PLAINTEXT_FILE" > "$ENC_FILE"
    rm "$PLAINTEXT_FILE"
}
(main $1)
