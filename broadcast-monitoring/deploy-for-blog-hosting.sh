#!/bin/bash -e

SCRIPT_NAME=`basename $0`
if [ $# -lt 1 ] && [ -z "${ENV_DEPLOY}" ]; then
  echo "Usage: ${SCRIPT_NAME} <environment>"
  exit 1
fi

ENV_DEPLOY="${ENV_DEPLOY:=$1}"
REGION=us-east-1
LAMBDA_DEPLOYMENT_BUCKET=broadcast-monitoring-blog

if [ $# -eq 3 ]
then
    LAMBDA_DEPLOYMENT_BUCKET=$2
    REGION=$3
fi


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
cd ${DIR}/infrastructure

VIDEO_PIPELINE_STACK_NAME=video-processing
TEMPLATE_NAME=video_processing.yaml

# install dependencies for shared lib.
# This is required because SAM build does not yet support dependencies of a layers folder
# https://github.com/awslabs/aws-sam-cli/issues/848
pip install -r ../src/sharedlib/requirements.txt -t ../src/sharedlib/

sam build -t ${TEMPLATE_NAME}

sam package \
   --s3-bucket ${LAMBDA_DEPLOYMENT_BUCKET} \
   --s3-prefix cloudformation/${VIDEO_PIPELINE_STACK_NAME}-${ENV_DEPLOY} \
   --region ${REGION} \
   --output-template-file ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml

aws s3 cp ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml s3://${LAMBDA_DEPLOYMENT_BUCKET}/cloudformation/video-processing.yml


# sam deploy deploy \
#      --template-file ingestion_and_processing_backend.yaml \
#      --stack-name broadcast-monitoring-${ENV_DEPLOY} \
#      --capabilities CAPABILITY_IAM \
#      --region ${REGION} \
#      --no-fail-on-empty-changeset

# Pass Template Parameters with the --parameter-overrides flag as necessary
# sam deploy \
#     --template-file ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml \
#     --stack-name ${VIDEO_PIPELINE_STACK_NAME}-${ENV_DEPLOY} \
#     --capabilities CAPABILITY_IAM \
#     --region ${REGION} \
#     --no-fail-on-empty-changeset

# # uncomment below to deploy elemental services
ELEMENTAL_STACK_NAME=elemental-services
TEMPLATE_NAME=elemental.yaml

sam build -t ${TEMPLATE_NAME}

sam package \
   --s3-bucket ${LAMBDA_DEPLOYMENT_BUCKET} \
   --s3-prefix cloudformation/${ELEMENTAL_STACK_NAME}-${ENV_DEPLOY} \
   --region ${REGION} \
   --output-template-file ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml

aws s3 cp ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml s3://${LAMBDA_DEPLOYMENT_BUCKET}/cloudformation/media-ingestion.yml

# # Pass Template Parameters with the --parameter-overrides flag as necessary
# sam deploy \
#     --template-file ${TEMPLATE_NAME}-${ENV_DEPLOY}-packaged.yaml \
#     --stack-name ${ELEMENTAL_STACK_NAME}-${ENV_DEPLOY} \
#     --capabilities CAPABILITY_IAM \
#     --region ${REGION} \
#     --parameter-overrides ProcessingBackendStackName=${VIDEO_PIPELINE_STACK_NAME}-${ENV_DEPLOY} \
#     --no-fail-on-empty-changeset


aws s3 cp ingestion_and_processing_backend.yaml s3://${LAMBDA_DEPLOYMENT_BUCKET}/cloudformation/backend.yml
