#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail


main() {
    python -m coverage run --branch --source=. -m pytest -vv
    coverage html
    coverage report
    echo "Cov: $(coverage report --format=total)%" > "/jaypore_ci/run/pytest.txt"
    # Mark info in jci docs
    # .. |Product| replace:: SoftTech Analyzer
    echo -e "\n.. |coverage| replace:: $(coverage report --format=total)%\n" >> "/jaypore_ci/run/docs/source/index.rst"
    echo -e "\n.. |package_version| replace:: $(poetry version | awk '{print $2}')\n" >> "/jaypore_ci/run/docs/source/index.rst"
}

(main)

