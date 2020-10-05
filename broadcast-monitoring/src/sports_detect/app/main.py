# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import os
import sys
import boto3
import json
from botocore.exceptions import ClientError

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.config import LOG_LEVEL, DDB_FRAME_TABLE, SPORTS_CHECK_CONFIG_KEY
from common.utils import check_enabled, DDBUpdateBuilder, convert_to_ddb

logging.basicConfig()
logger = logging.getLogger('SportsDetection')
logger.setLevel(LOG_LEVEL)

rekognition = boto3.client('rekognition')


class SportsCheck:
    def execute(self, expected_program_info, detected):
        """
        Compare the detected sport against the expected value
        :param expected: Expected Program data
        {
            "Team_Info": "AVL V NOR",
            "Station_Logo": "Prime Video",
                ...
            "Start_Time": 180,
            "languageCode": "en-en",
            "Sports_Type": "soccer",
            "Segment_Start_Time_In_Loop": 189.9875
        }
        :param detected:
          [
            {
              "Name": "soccer",
              "Confidence": 88.0790023803711,
            },
            ...
          ]
        """

        yield 'Sports_Expected', expected_program_info['Sports_Type']
        if not detected:
            # detection empty
            yield 'Sports_Status', False
        else:
            detected_sport = detected[0]['Name']
            yield 'Sports_Detected', detected_sport
            yield 'Sports_Detected_Confidence', detected[0]['Confidence']
            yield 'Sports_Status', detected_sport == expected_program_info['Sports_Type']


@check_enabled(SPORTS_CHECK_CONFIG_KEY)
def lambda_handler(event, context):
    """

    :param event: e.g.
    {
      "parsed": {...
      },
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": true,
        "language_detect_check_enabled": false,
        "team_detect_check_enabled": true,
        "sports_detect_check_enabled": true
      },
      "frame": {
        ...
        "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/10/23/42:43:646000.jpg",
        "Resized_S3_Key": "frames/test_video_single_pipeline/test_1/resized/2020/02/10/23/42:43:646000.jpg"
      }
    }
    :param context:
    :return:
    """

    frame_info = event['frame']
    bucket = frame_info['S3_Bucket']
    key = frame_info['S3_Key']
    min_confidence = int(os.getenv('SPORTS_MIN_CONFIDENCE', 60))
    model_arn = os.getenv('SPORTS_MODEL_ARN')

    logger.info('Sports Detection for image: %s', os.path.join(bucket, key))

    img_data = {'S3Object': {'Bucket': bucket, 'Name': key}}

    with DDBUpdateBuilder(key={'Stream_ID': frame_info['Stream_ID'], 'DateTime': frame_info['DateTime']},
                          table_name=DDB_FRAME_TABLE) as update_builder:
        try:
            response = rekognition.detect_custom_labels(
                Image=img_data, MinConfidence=min_confidence, ProjectVersionArn=model_arn
            )
        except ClientError as e:
            logger.error('Error calling detect)sports: %s', e)
            update_builder.update_attr('Sports_Detect_Error', e.response['Error']['Code'])
            raise e
        else:
            result = response.get('CustomLabels', [])

            if not result:
                logger.info('No sports detected')
            else:
                res_out = [f'{r["Name"]}: {r["Confidence"]}' for r in result]
                logger.info('Sports detected: %s', json.dumps(res_out, indent=4))

            # extract expected program
            expected_program = event['parsed']['expectedProgram']
            for name, value in SportsCheck().execute(expected_program, result):
                logger.info("Writing to %s [%s]: %s", DDB_FRAME_TABLE, name, value)
                update_builder.update_attr(name, value, convert_to_ddb)

        return result
