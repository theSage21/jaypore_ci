from    python:3.11 as jcibase
workdir /app
run     apt-get update
run     apt-get install ca-certificates curl gnupg lsb-release -y
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
env     PYTHONPATH=/jaypore_ci/run/

from jcienv as jci
add     jaypore_ci/ /app/jaypore_ci
run     poetry build
run     ls -alR dist
run     python3 -m pip install dist/jaypore_ci-*.whl
run     rm -rf jaypore_ci dist
run     ls -alR .
workdir /jaypore_ci/run/
