from    python:3.11 as jcienv
workdir /app

# Install docker

run     apt-get update && apt install -y wget curl zip vim ca-certificates gnupg
run     mkdir -m 0755 -p /etc/apt/keyrings
run     curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
run     echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
run     apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin


# SOPS

add     https://github.com/mozilla/sops/releases/download/v3.7.3/sops-v3.7.3.linux /bin/sops
add     https://github.com/FiloSottile/age/releases/download/v1.0.0/age-v1.0.0-linux-amd64.tar.gz ./age.tar.gz 
run     tar xf ./age.tar.gz && mv ./age/age /bin && mv ./age/age-keygen /bin && rm -rf ./age
run     chmod u+x /bin/sops /bin/age /bin/age-keygen

# Install python deps
run     python3 -m pip install --upgrade pip
run     python3 -m pip install poetry
add     pyproject.toml .
add     poetry.lock .
run     poetry config virtualenvs.create false
run     poetry install

env     PYTHONPATH=/jayporeci/run/:/app
env     PATH=/jayporeci/run/:/app:$PATH
env     EDITOR=vim

# Install jci library
from jcienv as jcilib
add     jayporeci/ /app/jayporeci
run     poetry build
run     ls -alR dist
run     python3 -m pip install dist/jayporeci-*.whl
run     rm -rf jayporeci dist
run     ls -alR .
workdir /jayporeci/run/

# Change entrypoint
from jcilib as jci
entrypoint ["/usr/local/bin/python", "-m", "jayporeci.cli"]
