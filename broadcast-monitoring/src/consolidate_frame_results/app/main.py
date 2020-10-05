# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import os
import sys

import boto3

# Conditionally add /opt to the PYTHON PATH
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.config import DDB_FRAME_TABLE, DDB_FRAGMENT_TABLE, LOG_LEVEL
from common.utils import DDBUpdateBuilder, get_item_ddb, convert_from_ddb, convert_to_ddb

from checks import station_logo_check, team_text_check, calculate_team_confidence, sports_check

logging.basicConfig()
logger = logging.getLogger('consolidate-frames')
logger.setLevel(LOG_LEVEL)

dynamodb = boto3.resource('dynamodb')


def consolidate_fragment_lambda_handler(event, context):
    """
    Processes the gathered results from the previous Map step of the frame processing pipeline
    and writes the results to dynamodb

    :param event: example
    {
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": false,
        "language_detect_check_enabled": true,
        "team_detect_check_enabled": false,
        "appsync_notify_enabled": true
      },
      "parsed": {
        "isMasterManifest": false,
        "streamId": "test_1",
        "lastSegment": {
          "s3Key": "live/test_video_single_pipeline/test_1_00043.ts",
          "versionId": "_ey0Mw8QDjqVgpCqUuE_v8tYlUVqd2Mo",
          "durationSec": 5.875,
          "startDateTime": "2020-02-22T22:15:59.375000Z",
          "startTimeRelative": 254.3
        },
        "expectedProgram": {
          "Team_Info": "AVL V NOR",
          "Station_Logo": "Prime Video",
          "Stream_ID": "test_1",
          "Event_Title": "EPL AVL V NOR",
          "Event_ID": "EPL-PROG3",
          "Event_Type": "Sports",
          "End_Time": 300,
          "Start_Time": 180,
          "languageCode": "en-en",
          "Segment_Start_Time_In_Loop": 254.3
        }
      },
      "frames": [
        {
          "Stream_ID": "test_1",
          "DateTime": "2020-02-19T22:45:14.938250Z",
            ...
          "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
          "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/19/22/45:14:938250.jpg"
        },
        {
          "Stream_ID": "test_1",
          "DateTime": "2020-02-19T22:45:17.941250Z",
            ...
          "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
          "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/19/22/45:17:941250.jpg"
        }
      ]
    }
    :param context: lambda environment context
    :return: None.  This step will write its results to DynamoDB
    """
    logger.info("DDB Frame Table: %s | DDB Fragment Table: %s", DDB_FRAME_TABLE, DDB_FRAGMENT_TABLE)
    config = event['config']
    stream_id = event['parsed']['streamId']
    segment_start_dt = event['parsed']['lastSegment']['startDateTime']

    # build test of checks from the enabled configs

    frame_checks = [station_logo_check, team_text_check, sports_check]

    active_configs = {k for k, v in config.items() if v}
    active_checks = [check for check in frame_checks if set(check.config_names).issubset(active_configs)]

    # test if any of the frame configs are active
    if not active_checks:
        logger.info('No active configurations to process.  Exiting frame consolidation')
        return

    # build a list of attributes to retrieve from DDB from the active checks
    data_attributes = ', '.join({attr for check in active_checks for attr in check.ddb_attrs})
    frame_data = []

    # get ddb attributes for each frame
    for frame in event['frames']:
        item = get_item_ddb(
            Key={'Stream_ID': frame['Stream_ID'], 'DateTime': frame['DateTime']},
            table_name=DDB_FRAME_TABLE,
            ProjectionExpression=data_attributes,
            ddb_client=dynamodb
        )

        frame_data.append(item)

    # update ddb row with results of each check
    with DDBUpdateBuilder(
            key={'Start_DateTime': segment_start_dt, 'Stream_ID': stream_id},
            table_name=DDB_FRAGMENT_TABLE,
            ddb_client=dynamodb
    ) as ddb_update_builder:
        # write attributes to the segment row from each check
        for result_name, result_data in check_processing_helper(active_checks, frame_data):
            ddb_update_builder.update_attr(result_name, result_data)

    logger.info('%d frame checks completed', len(active_checks))


def consolidate_team_data_lambda_handler(event, context):
    """
    Processes the team data from previous steps and merge the results from text and
    logo detection

    :param event: example
    {
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": false,
        "language_detect_check_enabled": true,
        "team_detect_check_enabled": false,
        "appsync_notify_enabled": true
      },
        ...
      "frames": [
        {
          "Stream_ID": "test_1",
          "DateTime": "2020-02-19T22:45:14.938250Z",
            ...
          "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
          "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/19/22/45:14:938250.jpg"
        },
        {
          "Stream_ID": "test_1",
          "DateTime": "2020-02-19T22:45:17.941250Z",
            ...
          "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
          "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/19/22/45:17:941250.jpg"
        }
      ]
    }
    :param context: lambda environment context
    :return: None.  This step will write its results to DynamoDB
    """
    config = event['config']

    # add the check to the active_checks list
    active_configs = {k for k, v in config.items() if v}
    team_checks_active = {k for k in active_configs if k in calculate_team_confidence.config_names}

    logger.info('Active team checks [%s]', team_checks_active)

    # test if any of the frame configs are active
    if not team_checks_active:
        logger.info('No team configurations active. Exiting frame consolidation')
        return

    # build a list of attributes to retrieve from DDB from the active checks
    data_attributes = ', '.join(calculate_team_confidence.ddb_attrs)

    # get ddb attributes for each frame
    for frame in event['frames']:
        s3_key = frame['S3_Key']
        frame_key = {'Stream_ID': frame['Stream_ID'], 'DateTime': frame['DateTime']}
        # get stored data for the frame to process
        frame_data = get_item_ddb(
            Key=frame_key,
            table_name=DDB_FRAME_TABLE,
            ProjectionExpression=data_attributes,
            ddb_update_builder=dynamodb
        )

        converted_data = convert_from_ddb(frame_data)

        # update ddb row with results of each check
        with DDBUpdateBuilder(
            key=frame_key,
            table_name=DDB_FRAME_TABLE,
            ddb_client=dynamodb
        ) as ddb_update_builder:
            # write attributes to the segment row from each check
            for result_name, result_data in consolidate_team_confidence(converted_data):
                ddb_update_builder.update_attr(result_name, result_data, convert_to_ddb)

        logger.info('Team data consolidated for frame: %s', s3_key)


def check_processing_helper(checks, frame_data):
    for check in checks:
        yield from check(frame_data)


def consolidate_team_confidence(frame_data):
    yield from calculate_team_confidence('Team1', frame_data)
    yield from calculate_team_confidence('Team2', frame_data)
