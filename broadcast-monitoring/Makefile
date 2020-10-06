
ARTIFACTS_BUCKET=broadcast-monitoring-blog
ENV_DEPLOY ?= dev
AWS_REGION ?= us-east-1

build.ingestion: ##=> Package media ingestion CloudFormation 
	$(info [*] Packaging media ingestion CloudFormation...)

	cd infrastructure && \
		sam build -t elemental.yaml && \ 
		sam package \
			--s3-bucket ${ARTIFACTS_BUCKET} \
			--s3-prefix cloudformation/media-ingest-${ENV_DEPLOY} \
			--region ${AWS_REGION} \
			--output-template-file media-ingest-${ENV_DEPLOY}-packaged.yaml && \
		aws s3 cp media-ingest-${ENV_DEPLOY}-packaged.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/media-ingestion.yml

build.processing: ##=> Package processing pipeline CloudFormation 
	$(info [*] Packaging processing pipeline CloudFormation...)

	cd infrastructure && \
		pip install -r ../src/sharedlib/requirements.txt -t ../src/sharedlib/ && \
		sam build -t video_processing.yaml && \
		sam package \
			--s3-bucket ${ARTIFACTS_BUCKET} \
		    --s3-prefix cloudformation/video-processing-${ENV_DEPLOY} \
			--region ${AWS_REGION} \
			--output-template-file video-processing-${ENV_DEPLOY}-packaged.yaml && \
		aws s3 cp video-processing-${ENV_DEPLOY}-packaged.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/video-processing.yml


build.parent:
	$(info [*] Upload parent stack CloudFormation...)
	cd infrastructure && \
		aws s3 cp ingestion_and_processing_backend.yaml s3://${ARTIFACTS_BUCKET}/cloudformation/backend.yml
