# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os
import logging
import json
import boto3
from urllib.parse import unquote_plus

# layers
import sys

sys.path.append('/opt')
from common.config import (LOG_LEVEL, STATION_LOGO_CHECK_CONFIG_KEY, TEAM_LOGO_CHECK_CONFIG_KEY, TEAM_CHECK_CONFIG_KEY,
                           REUSE_DETECTION_CONFIG_KEY, APPSYNC_NOTIFY_CONFIG_KEY, SPORTS_CHECK_CONFIG_KEY)
from common.utils import convert_str_to_bool

logger = logging.getLogger('StartSFN')
logger.setLevel(LOG_LEVEL)

SFN_ARN = os.getenv('SFN_ARN')
sfn_client = boto3.client('stepfunctions')


def lambda_handler(event, context):
    """
    Receive S3 put events and start a state machine execution for each s3 object
    :param event: S3 put event notification
    :param context: lambda environment context
    :return: none
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))
    for record in event['Records']:
        state_machine_input = parse_s3_event(record)

        response = sfn_client.start_execution(stateMachineArn=SFN_ARN, input=json.dumps(state_machine_input))
        logger.info(f'Started SFN execution: {response}')


def parse_s3_event(record):
    s3_bucket = record['s3']['bucket']['name']
    s3_key = unquote_plus(record['s3']['object']['key'])
    s3_version_id = record['s3']['object']['versionId']
    state_machine_input = {
        's3Bucket': s3_bucket,
        's3Key': s3_key,
        's3VersionId': s3_version_id,
        'config': {
            'audio_check_enabled': convert_str_to_bool(os.getenv('AUDIO_CHECK_ENABLED', "false")),
            STATION_LOGO_CHECK_CONFIG_KEY: convert_str_to_bool(os.getenv('STATION_LOGO_CHECK_ENABLED', "false")),
            TEAM_LOGO_CHECK_CONFIG_KEY: convert_str_to_bool(os.getenv('TEAM_LOGO_CHECK_ENABLED', "false")),
            TEAM_CHECK_CONFIG_KEY: convert_str_to_bool(os.getenv('TEAM_DETECT_CHECK_ENABLED', "false")),
            APPSYNC_NOTIFY_CONFIG_KEY: convert_str_to_bool(os.getenv('APPSYNC_NOTIFY_ENABLED', "false")),
            REUSE_DETECTION_CONFIG_KEY: convert_str_to_bool(os.getenv('REUSE_DETECTION_IF_AVAILABLE', "false")),
            SPORTS_CHECK_CONFIG_KEY: convert_str_to_bool(os.getenv('SPORTS_DETECT_CHECK_ENABLED', "false"))
        }
    }
    return state_machine_input
