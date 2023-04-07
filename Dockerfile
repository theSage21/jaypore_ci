from    python:3.11 as jcienv
workdir /app
run     python3 -m pip install --upgrade pip
run     python3 -m pip install poetry
add     pyproject.toml .
add     poetry.lock .
run     poetry config virtualenvs.create false
run     poetry install
env     PYTHONPATH=/jaypore_ci/run/:/app
env     PATH=/jaypore_ci/run/:/app:$PATH
env     EDITOR=vim
add     https://github.com/mozilla/sops/releases/download/v3.7.3/sops-v3.7.3.linux /bin/sops
add     https://github.com/FiloSottile/age/releases/download/v1.0.0/age-v1.0.0-linux-amd64.tar.gz ./age.tar.gz 
run     tar xf ./age.tar.gz && mv ./age/age /bin && mv ./age/age-keygen /bin && rm -rf ./age
run     apt update && apt install -y wget curl zip vim
run     chmod u+x /bin/sops /bin/age /bin/age-keygen

from jcienv as jci
add     jaypore_ci/ /app/jaypore_ci
run     poetry build
run     ls -alR dist
run     python3 -m pip install dist/jaypore_ci-*.whl
run     rm -rf jaypore_ci dist
run     ls -alR .
workdir /jaypore_ci/run/
entrypoint ["/usr/local/bin/python", "-m", "jaypore_ci.cli"]
