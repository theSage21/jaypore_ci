from    python:3.11 as jcibase
workdir /app
run     apt-get update
run     apt-get install ca-certificates curl zip gnupg lsb-release vim -y
run     mkdir -p /etc/apt/keyrings
run     curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
run     echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
run     apt-get update
run     apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin tree -y

from jcibase as jcienv
run     python3 -m pip install --upgrade pip
run     python3 -m pip install poetry
add     pyproject.toml .
add     poetry.lock .
run     poetry export --with dev > req.txt
run     python3 -m pip install -r req.txt
env     PYTHONPATH=/jaypore_ci/run/:/app
env     PATH=/jaypore_ci/run/:/app:$PATH
run     wget -O /bin/sops https://github.com/mozilla/sops/releases/download/v3.7.3/sops-v3.7.3.linux
run     wget -O ./age.tar.gz https://github.com/FiloSottile/age/releases/download/v1.0.0/age-v1.0.0-linux-amd64.tar.gz
run     tar xf ./age.tar.gz && mv ./age/age /bin && mv ./age/age-keygen /bin && rm -rf ./age
run     chmod u+x /bin/sops /bin/age /bin/age-keygen

from jcienv as jci
add     jaypore_ci/ /app/jaypore_ci
run     poetry build
run     ls -alR dist
run     python3 -m pip install dist/jaypore_ci-*.whl
run     rm -rf jaypore_ci dist
run     ls -alR .
workdir /jaypore_ci/run/
