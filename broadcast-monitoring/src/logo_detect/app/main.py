# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import json
import logging
import os
import sys

import boto3
from botocore.exceptions import ClientError

# Conditionally add /opt to the PYTHON PATH
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.config import LOG_LEVEL, DDB_FRAME_TABLE, STATION_LOGO_CHECK_CONFIG_KEY, TEAM_LOGO_CHECK_CONFIG_KEY
from common.utils import check_enabled, DDBUpdateBuilder, convert_to_ddb

logging.basicConfig()
logger = logging.getLogger('LogoDetection')
logger.setLevel(LOG_LEVEL)

rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')


@check_enabled(TEAM_LOGO_CHECK_CONFIG_KEY)
def team_logo_detect_lambda_handler(event, context):
    try:
        from .team_logo_check import TeamLogoCheck
    except ImportError:
        from team_logo_check import TeamLogoCheck

    lambda_handler(event, context, logo_check=TeamLogoCheck().execute)


@check_enabled(STATION_LOGO_CHECK_CONFIG_KEY)
def station_logo_detect_lambda_handler(event, context):
    try:
        from .station_logo_check import StationLogoCheck
    except ImportError:
        from station_logo_check import StationLogoCheck

    lambda_handler(event, context, logo_check=StationLogoCheck().execute)


def lambda_handler(event, context, logo_check=None):
    """
    This handler invokes a rekognition custom label model to detect and classify logos detected in
    a still frame image.

    :param event: exmample
    {
      "parsed": {...
      },
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": true,
        "language_detect_check_enabled": false,
        "team_detect_check_enabled": true
      },
      "frame": {
        ...
        "Stream_ID": "test_1",
        "DateTime": "2020-01-23T21:36:35.290000Z",
        "Chunk": "test_1_00016.ts",
        "Millis_In_Chunk": 0,
        "Frame_Num": 0,
        "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/01/23/21/36:35:290000.jpg"
      }
    }
    :param context: lambda context object

    """
    frame_info = event['frame']
    bucket = frame_info['S3_Bucket']
    key = frame_info['S3_Key']
    min_confidence = int(os.getenv('LOGO_MIN_CONFIDENCE', 60))
    model_arn = os.getenv('LOGO_MODEL_ARN')

    logger.info('Logo Detection for image: %s', os.path.join(bucket, key))

    img_data = {'S3Object': {'Bucket': bucket, 'Name': key}}

    with DDBUpdateBuilder(key={'Stream_ID': frame_info['Stream_ID'], 'DateTime': frame_info['DateTime']},
                          table_name=DDB_FRAME_TABLE, ddb_client=dynamodb) as update_builder:
        try:
            response = rekognition.detect_custom_labels(
                Image=img_data, MinConfidence=min_confidence, ProjectVersionArn=model_arn
            )
        except ClientError as e:
            logger.error('Error calling detect_custom_labels: %s', e)
            update_builder.update_attr('Logo_Detect_Error', e.response['Error']['Code'])
            raise e
        else:
            result = response.get('CustomLabels', [])
            # extract expected program
            expected_program = event['parsed']['expectedProgram']

            if not result:
                logger.info('No Logos detected')
            else:
                res_out = [f'{r["Name"]}: {r["Confidence"]}' for r in result]
                logger.info('Logos detected: %s', json.dumps(res_out, indent=4))

            for name, value in logo_check(expected_program, result):
                logger.info("Writing to %s [%s]: %s", DDB_FRAME_TABLE, name, value)
                update_builder.update_attr(name, value, convert_to_ddb)
