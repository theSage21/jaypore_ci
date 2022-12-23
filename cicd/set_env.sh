#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


export $(SOPS_AGE_KEY_FILE=secrets/jaypore_ci.age  sops --decrypt --input-type dotenv --output-type dotenv secrets/jaypore_ci.enc | xargs)
