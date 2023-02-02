#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


main() {
    python -m coverage run --source=. -m pytest -vv
    coverage html
    coverage report
    echo "$(coverage report --format=total)%" > "/jaypore_ci/run/pytest.txt"
}

(main)

