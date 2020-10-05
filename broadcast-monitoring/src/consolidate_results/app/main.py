# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os
import logging
import sys
import json

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.utils import convert_float_to_dec, convert_dict_float_to_dec, check_enabled, DDBUpdateBuilder, get_item_ddb
from common.config import (LOG_LEVEL, DDB_FRAGMENT_TABLE, STATION_LOGO_CHECK_CONFIG_KEY, TEAM_CHECK_CONFIG_KEY,
                           SPORTS_CHECK_CONFIG_KEY)

logging.basicConfig()
logger = logging.getLogger('FindExpectedProgramMain')
logger.setLevel(LOG_LEVEL)

# this is the order of the processing steps defined in Step Functions,
# which result in the output being in the same order
AUDIO_RESULT = 0
FRAME_RESULT = 1


def lambda_handler(event, context):
    """
    Process results from preceding steps in the workflow to determine status for each check being performed.
    Persist the computed status and raw data into DDB.
    :param event:
    {
      "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
      "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
      "s3VersionId": "J5c7s6IZYD9TIt.BM5Zj53ku1l6rw1M9",
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
                "versionId": "ZQcYoj5uiDgaAU0lkukuHCS2zyh5NXM0",
                "startDateTime": "2020-01-23T21:36:35.290000Z",
                "durationSec": 6
            },
            "expectedProgram"{
                ...
            }
        }
      "detections":{
        [
          {
            "volume": {
              "mean": -29.2,
              "max": -13.9
            },
            "silence_chunks": []
          },
          {
             "expected": {
                 "lanaguageCode": "en-en",
                 "languageName": "English"
             },
             "dectected": {
                 "languageCode": "en-en",
                 "languageName": "English",
                 "confidence": 0.8843594193458557
             }
           },
          []
        ]
      }
    }
    :return:
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))
    segment_start_dt = event['parsed']['lastSegment']['startDateTime']
    stream_id = event['parsed']['streamId']
    segment_relative_start_time = event['parsed']['lastSegment']['startTimeRelative']
    segment_start_time_in_loop = event['parsed']['expectedProgram']['Segment_Start_Time_In_Loop']
    segment_duration = event['parsed']['lastSegment']['durationSec']

    segment_table_key = {'Start_DateTime': segment_start_dt, 'Stream_ID': stream_id}
    with DDBUpdateBuilder(key=segment_table_key, table_name=DDB_FRAGMENT_TABLE) as ddb_update_builder:
        ddb_update_builder.update_attr('Start_Time_Sec', convert_float_to_dec(segment_relative_start_time))
        ddb_update_builder.update_attr('Start_Time_Sec_In_Loop', convert_float_to_dec(segment_start_time_in_loop))
        ddb_update_builder.update_attr('Finished', True)

        audio_on_status = process_audio_check(event, ddb_update_builder, segment_duration)
        station_status = get_station_logo_status(event, segment_table_key)
        team_status = get_team_status(event, segment_table_key)
        sports_status = get_sports_status(event, segment_table_key)
    status_summary = {
        'Audio_Status': audio_on_status,
        'Station_Status': station_status,
        'Team_Status': team_status,
        'Sports_Status': sports_status
    }

    frames = event['detections'][FRAME_RESULT]
    thumbnail_s3_key = frames[0]['S3_Key']

    event['thumbnailKey'] = thumbnail_s3_key
    event['statusSummary'] = status_summary
    return event


@check_enabled(STATION_LOGO_CHECK_CONFIG_KEY)
def get_station_logo_status(event, segment_table_key):
    # TODO: modify the state machine so this result get passed from previous processing to save a call to DDB
    item = get_item_ddb(
        table_name=DDB_FRAGMENT_TABLE, Key=segment_table_key, AttributesToGet=['Station_Status']
    )
    return item.get('Station_Status', None)


@check_enabled(TEAM_CHECK_CONFIG_KEY)
def get_team_status(event, segment_table_key):
    # TODO: modify the state machine so this result get passed from previous processing to save a call to DDB
    item = get_item_ddb(
        table_name=DDB_FRAGMENT_TABLE, Key=segment_table_key, AttributesToGet=['Team_Status']
    )
    return item.get('Team_Status', None)


@check_enabled(SPORTS_CHECK_CONFIG_KEY)
def get_sports_status(event, segment_table_key):
    # TODO: modify the state machine so this result get passed from previous processing to save a call to DDB
    item = get_item_ddb(
        table_name=DDB_FRAGMENT_TABLE, Key=segment_table_key, AttributesToGet=['Sports_Status']
    )
    return item.get('Sports_Status', None)


@check_enabled("audio_check_enabled")
def process_audio_check(event, ddb_update_builder, segment_duration):
    audio = event['detections'][AUDIO_RESULT]

    if "Error" in audio:
        ddb_update_builder.update_attr('Audio_Check_Error', audio["Error"])
        return None
    # process results for audio detection
    audio_on_status, silence_duration, silence_confidence = eval_audio_status(audio, segment_duration)
    if 'volume' in audio:
        ddb_update_builder.update_attr('Volume', convert_dict_float_to_dec(audio['volume']))
    ddb_update_builder.update_attr('Silence', json.dumps(audio['silence_chunks']))
    ddb_update_builder.update_attr('Audio_Status', audio_on_status)
    ddb_update_builder.update_attr('Silence_Duration', convert_float_to_dec(silence_duration))
    ddb_update_builder.update_attr('Silence_Confidence', convert_float_to_dec(silence_confidence))
    logger.info(f'Audio on status: {audio_on_status}')
    return audio_on_status


def eval_audio_status(audio, segment_duration):
    silence_duration = sum([chunk['end'] - chunk['start'] for chunk in audio['silence_chunks']])
    silence_percentage = silence_duration / segment_duration if segment_duration > 0 else 0
    logger.info(f'Silence: {silence_duration} / {segment_duration} = {silence_percentage}')
    # TODO: add support for looking back
    audio_on_status = silence_percentage <= 0.5
    silence_confidence = min(100, (0.5 + abs(0.5 - silence_percentage)) * 100.0)
    return audio_on_status, silence_duration, silence_confidence


if __name__ == '__main__':
    input = {
        "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
        "s3VersionId": "Y7ULvcAFF2hEF_hGMQBxRAXRf73qotMZ",
        "config": {
            "audio_check_enabled": True,
            "station_logo_check_enabled": False,
            "language_detect_check_enabled": True,
            "team_detect_check_enabled": True
        },
        "parsed": {
            "isMasterManifest": True,
            "streamId": "test_1",
            "lastSegment": {
                "s3Key": "live/test_video_single_pipeline/test_1_00019.ts",
                "versionId": "ehiZLOCovZPH0hBukYPl7nIGfeUHYC5t",
                "durationSec": 7.5075,
                "startDateTime": "2020-02-18T23:34:18.426500Z",
                "startTimeRelative": 137.435
            },
            "expectedProgram": {
                "Station_Logo": "ABC",
                "Stream_ID": "test_1",
                "Event_Title": "Variety show 123",
                "Event_ID": "SIM-PROG2",
                "Event_Type": "Variety show",
                "End_Time": 180,
                "Start_Time": 90,
                "Audio": "Russian",
                "Segment_Start_Time_In_Loop": 137.435
            }
        },
        "detections": [
            {
                "volume": {
                    "mean": -11.4,
                    "max": -3.2
                },
                "silence_chunks": []
            },
            [{"S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/17/23/34:10:919500.jpg"}]
        ]
    }

    lambda_handler(input, None)
