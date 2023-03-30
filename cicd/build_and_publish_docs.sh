#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail

build() {
    echo "Cleaning docs build"
    touch docs/build
    rm -rf docs/build && mkdir -p docs/build
    ls -al docs
    echo "Building docs"
    sphinx-apidoc -o docs/source/reference ./jaypore_ci
    (python3 cicd/render_changelog.py >> docs/source/index.rst)
    sphinx-build docs/source/ docs/build
    sphinx-build docs/source/ docs/build -b coverage

    # Create pre-push for repo
    PREPUSH=docs/build/pre-push.sh
    cp cicd/pre-push.sh $PREPUSH
    sed -i '$ d' $PREPUSH
    # add expected version of Jci
    echo "" >> $PREPUSH
    echo "# Change the version in the next line to whatever you want if you" >> $PREPUSH
    echo "# would like to upgrade to a different version of JayporeCI." >> $PREPUSH
    echo -n "EXPECTED_JAYPORECI_" >> $PREPUSH
    grep version pyproject.toml | python3 -c 'print(input().upper().replace(" ", "").replace("\"", ""))' >> $PREPUSH

    echo "" >> $PREPUSH
    echo '("$@")' >> $PREPUSH

    # Copy other files
    cp cicd/Dockerfile docs/build
    cp setup.sh docs/build
    cp -r htmlcov /jaypore_ci/run/docs/build/
    cp -r secrets/bin docs/build
    wget -O docs/build/sops https://github.com/mozilla/sops/releases/download/v3.7.3/sops-v3.7.3.linux
    wget -O ./age.tar.gz https://github.com/FiloSottile/age/releases/download/v1.0.0/age-v1.0.0-linux-amd64.tar.gz
    tar xf ./age.tar.gz && mv ./age/age docs/build/bin && mv ./age/age-keygen docs/build/bin && rm -rf ./age

    # Create docs bundle
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
