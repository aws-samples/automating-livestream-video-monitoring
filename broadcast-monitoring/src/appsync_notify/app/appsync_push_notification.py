# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os
import logging
import sys
import json
import requests

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.config import APPSYNC_API_ENDPOINT_URL, APPSYNC_API_KEY, LOG_LEVEL

logger = logging.getLogger('AppSyncPushNotification')
logger.setLevel(LOG_LEVEL)


def execute_gql(gql_query, params={}):
    """
    Utitliy function that executes GraphQL queries
    :param gql_query: GraphQL query (can be query, mutation, subscription, etc.)
    :param params: variable arguments
    :return: response from graph QL server
    """
    headers = {
        'Content-Type': "application/graphql",
        'x-api-key': APPSYNC_API_KEY,
        'cache-control': "no-cache",
    }
    logger.debug(f'graphQL request headers: {headers}')

    payload_obj = {"query": gql_query, "variables": json.dumps(params)}
    payload = json.dumps(payload_obj)
    logger.debug(f'graphQL request payload: {payload}')

    response = requests.request("POST", APPSYNC_API_ENDPOINT_URL, data=payload, headers=headers)
    logger.info(f'graphQL response: {json.loads(response.content.decode("utf-8"))}')
    return response


def push_appsync(stream_id, segment_start_date_time_str, segment_duration_sec, segment_s3_key, thumbnail_s3_key,
                 media_check_status):
    """
    Notify AppSync subscribers that a new segment summary is available.
    :param stream_id:
    :param segment_start_date_time_str:
    :param segment_duration_sec:
    :param segment_s3_key:
    :param thumbnail_s3_key:
    :param media_check_status:
    :return: none
    """

    new_segment_ready_gql = '''
    mutation NewSegmentSummaryReady($input: newSegmentSummaryReadyInput!) {
      newSegmentSummaryReady(input: $input) {
        Stream_ID
        Start_DateTime
        Duration_Sec
        S3_Key
        Station_Status
        Audio_Status
        Sports_Status
        Team_Status
        Thumbnail_Key
      }
    }
    '''

    new_segment_summary_ready_input = {
        "Stream_ID": stream_id,
        "Start_DateTime": segment_start_date_time_str,
        "Duration_Sec": segment_duration_sec,
        "S3_Key": segment_s3_key,
    }
    if thumbnail_s3_key is not None:
        new_segment_summary_ready_input['Thumbnail_Key'] = thumbnail_s3_key

    for checks in media_check_status:
        new_segment_summary_ready_input[checks] = media_check_status[checks]

    execute_gql(new_segment_ready_gql, params={"input": new_segment_summary_ready_input})
    logger.info('success pushing to AppSync.')
