# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
# layers
import sys

sys.path.append('/opt')

try:
    from .team_text_check import TeamCheck
except ImportError:
    from team_text_check import TeamCheck

from common.utils import detect_text_from_image, check_enabled, DDBUpdateBuilder
from common.config import LOG_LEVEL, DDB_FRAME_TABLE, TEAM_CHECK_CONFIG_KEY

logging.basicConfig()
logger = logging.getLogger('TextInImage')
logger.setLevel(LOG_LEVEL)


@check_enabled(TEAM_CHECK_CONFIG_KEY)
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
        "team_detect_check_enabled": true
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
    s3_bucket = frame_info['S3_Bucket']
    s3_key = frame_info['S3_Key']
    detected_text_response = detect_text_from_image(s3_bucket, s3_key)
    logger.debug(f'detect text response: {detected_text_response}')

    detected_lines = [entry['DetectedText'] for entry in detected_text_response if entry['Type'] == 'LINE']
    detected_words = [entry['DetectedText'] for entry in detected_text_response if entry['Type'] == 'WORD']

    check = TeamCheck()
    result = check.execute(event['parsed']['expectedProgram'], detected_text_response)

    with DDBUpdateBuilder(key={'Stream_ID': frame_info['Stream_ID'], 'DateTime': frame_info['DateTime']},
                          table_name=DDB_FRAME_TABLE) as ddb_update_builder:
        ddb_update_builder.update_attr('Detected_Lines', detected_lines)
        ddb_update_builder.update_attr('Detected_Words', detected_words)

        if result:
            for name, value in result.items():
                ddb_update_builder.update_attr(name, value)


if __name__ == '__main__':
    s3_bucket = 'aws-rnd-broadcast-maas-data'
    s3_key = 'frames/test_video_single_pipeline/test_1/original/2020/01/21/16/59:08:002000.jpg'
    lambda_handler({
        'S3_Bucket': s3_bucket,
        'S3_Key': s3_key
    }, None)
    # detected_text_response = detect_text_from_image(s3_bucket, s3_key)
    # print(detected_text_response)
    # teams = detect_team_from_text_in_image(detected_text_response)
    # print(json.dumps(teams, indent=2))
