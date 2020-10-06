## Automating broadcast video monitoring using machine learning - blog post and sample application

In the M&E industry, monitoring live broadcast and OTT video streams has largely been a manual process relying on human operators constantly watching the stream to identify quality or content issues. Latest advances in artificial intelligence(AI) can help automate many monitoring tasks that was once manual and support monitoring at greater scale. This repo presents a demo application for realtime livestream monitoring using AWS serverless and AI/ML services.

Read more on the accompanying [blog post]().

### Architecture

The solution architecture for the application consists of three main components:

- A video ingestion pipeline where HLS streams produced by AWS Elemental MediaLive is stored in an Amazon S3 bucket
- A video processing pipeline orchestrated by AWS Step Functions that performs monitoring checks on extracted frames and audio from each video segment
- A web application that demonstrates the realtime status and details of each monitoring check being performed on the video stream

![./img/architecture.png](./img/architecture.png)

### Deploying the video ingestion pipeline and video processing pipeline

This section discuss how to deploy the Video ingestion and processing pipeline component of the sample application

#### Option 1: One-click deployment

Follow the below for a quick way to deploy the sample pipeline.

1. Using the following button to start launching a CloudFormation stack:

   [![button to launch cloudformation stack](./img/launch-cloudformation.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=broadcast-monitoring&templateURL=https://s3.amazonaws.com/broadcast-monitoring-blog/cloudformation/backend.yml)

1. Select the **Next** button to continue
1. In **Step 2: Specify stack details** review the stack parameters.
   These settings configures the source of the HLS stream the AWS Elemental MediaLive pipeline will be producing and monitored by the application. Keep the default to generate a test stream using a sample mp4 file hosted on S3. You can change these settings at this point to to point to your own video files/streams.

   Once the stack is created, you can also change the input configuration any time by doing so in the AWS Elemental MediaLive console (The AWS Elemental MediaLive pipeline allows switching between different input sources seamlessly as long as you stop the pipeline before making changes)

1. Click the **Next** button. In **Step 3 Configure stack options** page, keep all defaults, and click **Next** again
1. In **Step 4 Review** page, click the checkmarks to acknowledge CloudFormation will be creating IAM resources and the `CAPABILITY_AUTO_EXPAND` capability, and then click “**Create stack**”.
1. Wait for the stack creation to complete

#### Option 2: build from source

If you would like to develop on top of the application and make changes, you can also build and deploy the application from source

1. Fork the repo
2. clone to local workspace using `git clone`
3. Source code for the Video ingestion and processing pipeline components is under `broadcast-monitoring` subdirectory. Navigate to the directory:

   ```
   cd broadcast-monitoring/
   ```

4. initialize pipenv

   ```
   pipenv install
   ```

5. In the `Makefile`, fill in your own S3 bucket name in `ARTIFACTS_BUCKET=<your-s3-bucket>` to be used for packaging Lambda code
6. Run the make targets to build and deploy the processing pipeline.

   ```
   pipenv run make	build.processing
   pipenv run make	deploy.processing
   ```

   This will create:

   - A S3 bucket
   - A Step Functions state machine,
   - A Lambda function that starts the Step Functions state machine when the S3 bucket has a new manifest file
   - DynamoDB tables to store schedule metadata and media analysis results

7) After the processing pipeline finish deploying , build and deploy the media ingest pipeline:

   ```shel
   pipenv run make build.mediaingest
   pipenv run make deploy.mediaingest
   ```

   This will create:

   - An AWS Elemental MediaLive channel with a MediaLive input (configured by the CloudFormation input parameters)
   - An AWS Elemental MediaPackage channel connected to the MediaLive channel
   - A CloudFront distribution connected to the MediaPackage channel

## Reporting security issues

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
