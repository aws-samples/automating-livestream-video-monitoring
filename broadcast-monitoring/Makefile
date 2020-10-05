ARTIFACTS_BUCKET=broadcast-monitoring-blog
ENV_DEPLOY ?= test
AWS_REGION ?= us-east-1



build.processing: ##=> Package processing pipeline CloudFormation 
	$(info [*] Packaging processing pipeline CloudFormation...)

	cd infrastructure && \
		pip install -r ../src/sharedlib/requirements.txt -t ../src/sharedlib/ && \
		sam build -t video_processing.yaml && \
		sam package \
			--s3-bucket ${ARTIFACTS_BUCKET} \
		    --s3-prefix cloudformation/video-processing-${ENV_DEPLOY}\
			--region ${AWS_REGION} \
			--output-template-file video-processing-${ENV_DEPLOY}-packaged.yaml

deploy.processing:
	$(info [*] Deploying media processing CloudFormation...)
	cd infrastructure && \
	 sam deploy \
		  --template-file video-processing-${ENV_DEPLOY}-packaged.yaml \
		  --stack-name video-processing-${ENV_DEPLOY} \
		  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		  --region ${AWS_REGION} \
		  --no-fail-on-empty-changeset

build.mediaingest:
	$(info [*] Packaging media ingestion CloudFormation...)
	cd infrastructure && \
		sam build -t elemental.yaml && \
		sam package \
			--s3-bucket ${ARTIFACTS_BUCKET} \
			--s3-prefix cloudformation/media-ingest-${ENV_DEPLOY} \
			--region ${AWS_REGION} \
			--output-template-file media-ingest-${ENV_DEPLOY}-packaged.yaml


deploy.mediaingest:
	$(info [*] Deploying media ingestion CloudFormation...)
	$(eval PROCESSING_BUCKET := $(shell aws cloudformation list-exports --query "Exports[?Name==\`video-processing-${ENV_DEPLOY}-VideoProcessingBucket\`].Value" --no-paginate --output text))

	$(info [*] PROCESSING_BUCKET: ${PROCESSING_BUCKET})
	cd infrastructure && \
		sam deploy \
			 --template-file media-ingest-${ENV_DEPLOY}-packaged.yaml \
			 --stack-name media-ingest-${ENV_DEPLOY} \
			 --capabilities CAPABILITY_IAM \
			 --region ${AWS_REGION} \
			 --parameter-overrides VideoProcessingBucket=${PROCESSING_BUCKET} \
			 --no-fail-on-empty-changeset

host.processing:
	$(info [*] Upload mediap processing CloudFormation to hosting bucket...)
	cd infrastructure && \
		aws s3 cp video-processing-${ENV_DEPLOY}-packaged.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/video-processing.yml

host.mediaingest: ##=> Package media ingestion CloudFormation
	$(info [*] Upload media ingestion CloudFormation to hosting bucket...)
	cd infrastructure && \
		aws s3 cp media-ingest-${ENV_DEPLOY}-packaged.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/media-ingestion.yml

host.nested:
	$(info [*] Upload parent stack CloudFormation...)
	cd infrastructure && \
		aws s3 cp ingestion_and_processing_backend.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/backend.yml
