#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail

main() {
    echo "v$(poetry version | awk '{print $2}')" > "/jaypore_ci/run/PublishPypi.txt"
    poetry build
    poetry config pypi-token.pypi $PYPI_TOKEN
    poetry publish
}
(main)
