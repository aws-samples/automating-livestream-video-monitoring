import boto3
import fire
import re

client = boto3.client('rekognition')

version_name_re = re.compile(r'version/(?P<version_name>[a-zA-Z0-9_.\-]{1,255})/[0-9]+')


def start_model(project_arn, model_arn, min_inference_units=1):

    res = version_name_re.search(model_arn)
    version_name = res.group('version_name')

    try:
        # Start the model
        print('Starting model: ' + model_arn)
        client.start_project_version(ProjectVersionArn=model_arn, MinInferenceUnits=min_inference_units)
        # Wait for the model to be in the running state
        project_version_running_waiter = client.get_waiter('project_version_running')
        project_version_running_waiter.wait(ProjectArn=project_arn, VersionNames=[version_name])

        # Get the running status
        describe_response = client.describe_project_versions(ProjectArn=project_arn, VersionNames=[version_name])
        for model in describe_response['ProjectVersionDescriptions']:
            print("Status: " + model['Status'])
            print("Message: " + model['StatusMessage'])
    except Exception as e:
        print(e)

    print('Done...')


def stop_model(model_arn):

    print('Stopping model:' + model_arn)

    try:
        response = client.stop_project_version(ProjectVersionArn=model_arn)
        status = response['Status']
        print('Status: ' + status)
    except Exception as e:
        print(e)

    print('Done...')


if __name__ == "__main__":
    fire.Fire()
