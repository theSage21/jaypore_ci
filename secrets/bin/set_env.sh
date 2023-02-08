#!/usr/bin/env bash

BIN=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SECRETS=$(echo "$BIN/..")
NAME=$1
PATH="$BIN:$PATH"
export $(SOPS_AGE_KEY_FILE=$SECRETS/$NAME.key sops --decrypt --input-type dotenv --output-type dotenv $SECRETS/$NAME.enc | xargs)
