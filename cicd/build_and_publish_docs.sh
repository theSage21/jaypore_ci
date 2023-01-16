#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail

build() {
    echo "Building docs"
    sphinx-apidoc -o docs/source/reference ./jaypore_ci
    sphinx-build docs/source/ docs/build
    (cd docs/build && zip -r ../../website.zip ./)
}

publish() {
    echo "Publishing docs"
    curl -H "Content-Type: application/zip" \
         -H "Authorization: Bearer $NETLIFY_TOKEN" \
         --data-binary "@website.zip" \
         https://api.netlify.com/api/v1/sites/$NETLIFY_SITEID/deploys
}

(build)
(publish)
