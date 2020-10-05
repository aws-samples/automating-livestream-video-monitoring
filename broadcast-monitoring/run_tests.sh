#!/bin/bash
set -e

# start local dynamodb docker
docker pull amazon/dynamodb-local
echo "------------STARTING DDB DOCKER----------------"
cid=$(docker run -d -p 8000:8000 amazon/dynamodb-local)

echo "docker container id: $cid"
# stop the local dynamodb
trap "docker stop $cid && echo '------------DDB DOCKER STOPPED----------------' " EXIT

# Unit Tests
echo "------------UNIT TESTS START----------------"
pytest
echo "------------UNIT TESTS END----------------"

# Lint
echo "------------FLAKE8 LINT START----------------"
flake8
echo "------------FLAKE8 LINT END----------------"
