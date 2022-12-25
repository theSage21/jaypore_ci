#! /bin/bash

set -o errexit
set -o nounset
set -o pipefail

docker login -u arjoonn -p=$DOCKER_PWD
docker build --target $1 -t $1:latest .
docker tag $1:latest arjoonn/$1:latest
docker push arjoonn/$1:latest
