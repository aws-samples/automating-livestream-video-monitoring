# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import re
import subprocess
import os
import sys
from boto3.dynamodb.conditions import Key, Attr
import logging

try:
    from .find_expected_program import find_expected_program_for_looping_input
except ImportError:
    from find_expected_program import find_expected_program_for_looping_input

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.utils import download_file_from_s3, cleanup_dir, query_item_ddb, convert_float_to_dec, check_enabled
from common.config import (LOG_LEVEL, TEAM_CHECK_CONFIG_KEY, TEAM_LOGO_CHECK_CONFIG_KEY, DDB_FRAGMENT_TABLE,
                           REUSE_DETECTION_CONFIG_KEY, SPORTS_CHECK_CONFIG_KEY)

logging.basicConfig()
logger = logging.getLogger('FindExpectedProgramMain')
logger.setLevel(LOG_LEVEL)

start_time_pattern = re.compile(r'start_time=(?P<start>[0-9]+(\.?[0-9]*))')


def get_relative_start_sec(video_file):
    o = subprocess.check_output(
        ["ffprobe", "-show_entries", "format=start_time", "-of", "default=noprint_wrappers=1", video_file])
    output = o.decode('utf-8')
    start_time_re_match = start_time_pattern.search(output)
    start_sec = float(start_time_re_match.group('start'))
    logger.info(f'Found {video_file} relative start time: {start_sec}')
    return start_sec


@cleanup_dir()
def lambda_handler(event, context):
    """

    :param event:
    {
      "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
      "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
      "s3VersionId": "KJCfz6c8Il5E_23jbzwYuFhGIpvMnrJE",
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": true,
        "language_detect_check_enabled": true,
        "team_detect_check_enabled": true,
        "appsync_notify_enabled": true
      },
      "parsed": {
        {
            "isMasterManifest": false,
            "streamId": "test_1",
            "lastSegment": {
                "s3Key": "live/test_video_single_pipeline/test_1_00039.ts",
                "startDateTime": "2020-01-23T21:36:35.290000Z",
                "durationSec": 6
            }
          }
      }
    }
    :return:
    """
    manifest_s3_bucket = event['s3Bucket']
    segment_s3_key = event['parsed']['lastSegment']['s3Key']
    stream_id = event['parsed']['streamId']
    # the cleanup_dir decorator will ensure the tmp/ working directory gets cleaned up if lambda container is reused
    segment_file = download_file_from_s3(manifest_s3_bucket, segment_s3_key)
    start_time = get_relative_start_sec(segment_file)
    duration_sec = event['parsed']['lastSegment']['durationSec']
    # TODO: add support for if the input stream is actual live video
    #  (perhaps a slightly different lookup mechanism based on absolute timestamp)
    expected_program = find_expected_program_for_looping_input(stream_id, start_time, duration_sec)
    event['parsed']['lastSegment']['startTimeRelative'] = start_time
    event['parsed']['expectedProgram'] = expected_program

    available_detection = check_available_detection(event, stream_id, expected_program['Segment_Start_Time_In_Loop'],
                                                    event['parsed']['lastSegment']['startDateTime'],
                                                    duration_sec)
    if available_detection:
        event['reuse'] = {
            'enabled': True,
            'segment': available_detection
        }
    else:
        event['reuse'] = {
            'enabled': False
        }

    # disable team check when there's no expected team in program
    if 'Team_Info' not in expected_program:
        event['config'][TEAM_CHECK_CONFIG_KEY] = False
        event['config'][TEAM_LOGO_CHECK_CONFIG_KEY] = False
    # disable sports check when the program is not sports
    if 'Sports_Type' not in expected_program:
        event['config'][SPORTS_CHECK_CONFIG_KEY] = False

    return event


@check_enabled(REUSE_DETECTION_CONFIG_KEY)
def check_available_detection(event, stream_id, start_time_in_program_loop, start_datetime, duration_sec):
    """
    If the playlist is looping and reuse detection is enabled, look up past detections for the same video segment
    :return The absolute start time of the past detection to reuse.
    """
    # look up past detections that share the same Start_Time_Sec_In_Loop attr with the current segment
    query_params = {
        'IndexName': 'Stream_ID_Start_In_Loop',
        'ScanIndexForward': False,
        'KeyConditionExpression': Key('Stream_ID').eq(stream_id) & Key('Start_Time_Sec_In_Loop').eq(
            convert_float_to_dec(start_time_in_program_loop)),
        'FilterExpression': Attr('Finished').eq(True) & Attr('Start_DateTime').ne(start_datetime) & Attr(
            'Duration_Sec').eq(convert_float_to_dec(duration_sec))
    }
    logger.info(f'{query_params}')
    result = query_item_ddb(DDB_FRAGMENT_TABLE, **query_params)
    if result:
        # reuse the most recent past detection
        logger.info(f'Found existing detections: {len(result)}')
        return result[0]['Start_DateTime']
    else:
        logger.info('Did not find existing detections to reuse.')
        return None


# for local testing
if __name__ == '__main__':
    test_event = {
        "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
        "s3VersionId": "LpFHyIwcGt20C8S5sCt9qpIF3Qd.KU.t",
        "parsed": {
            "isMasterManifest": False,
            "streamId": "test_1",
            "lastSegment": {
                "s3Key": "live/test_video_single_pipeline/test_1_00137.ts",
                "durationSec": 6.006,
                "startDateTime": "2020-01-31T22:27:16.550000Z"
            }
        }
    }
    lambda_handler(test_event, None)
