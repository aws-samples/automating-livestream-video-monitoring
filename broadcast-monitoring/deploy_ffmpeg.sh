#!/bin/bash -e

ENV_DEPLOY=${1:-dev}
REGION=us-east-1
LAMBDA_DEPLOYMENT_BUCKET=artifacts-206038983416-${REGION}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

# update to project specific names:
TEMPLATE_PATH="${DIR}/infrastructure/ffmpeg.yaml"
TEMPLATE_NAME="$(basename -s .yaml $TEMPLATE_PATH)"

OUT_TEMPLATE_FILE=${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml
STACK_NAME=ffmpeg-layer-${ENV_DEPLOY}

sam build -t ${TEMPLATE_PATH}

sam package \
   --s3-bucket ${LAMBDA_DEPLOYMENT_BUCKET} \
   --s3-prefix ${STACK_NAME} \
   --region ${REGION} \
   --output-template-file ${OUT_TEMPLATE_FILE}

# Pass Template Parameters with the --parameter-overrides flag as necessary
sam deploy \
    --template-file ${OUT_TEMPLATE_FILE} \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --region ${REGION} \
    --no-fail-on-empty-changeset
