#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail

main() {
    poetry build
    poetry config pypi-token.pypi $PYPI_TOKEN
    poetry publish
}
(main)
