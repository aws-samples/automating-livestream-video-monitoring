import json
import os

import pytest
from botocore.stub import Stubber

from ..app.main import rekognition, dynamodb, lambda_handler

TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv('LOGO_MIN_CONFIDENCE', '60')
    monkeypatch.setenv('LOGO_MODEL_ARN', 'arn:aws:rekognition:us-east-1:206038983416:test')


@pytest.fixture
def inbound_step_event():
    """Inbound step event"""

    return {
        "parsed": {
            "expectedProgram": {},
        },
        "config": {
            "station_logo_check_enabled": True
        },
        "frame": {
            "Stream_ID": "test_1",
            "DateTime": "2020-01-23T21:36:35.290000Z",
            "Chunk": "test_1_00016.ts",
            "Millis_In_Chunk": 0,
            "Frame_Num": 0,
            "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
            "S3_Key": "frames/test.jpg"
        }
    }


@pytest.fixture
def rekognition_stub():
    with Stubber(rekognition) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def ddb_test_table_stub():
    test_table = dynamodb.Table('')
    with Stubber(test_table.meta.client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def response_data():
    test_data_path = os.path.join(TEST_DATA_DIR, 'rekognition_response.json')
    with open(test_data_path, 'r') as f:
        return json.load(f)


def test_lambda_handler(rekognition_stub, ddb_test_table_stub, inbound_step_event, response_data):
    rekognition_expected_params = {
        'MinConfidence': 60,
        'ProjectVersionArn': 'arn:aws:rekognition:us-east-1:206038983416:test',
        'Image': {
            'S3Object': {
                'Bucket': 'aws-rnd-broadcast-maas-video-processing-dev',
                'Name': 'frames/test.jpg'
            }
        }
    }

    rekognition_stub.add_response('detect_custom_labels', response_data, rekognition_expected_params)
    lambda_handler(inbound_step_event, '', lambda x, y: [])
