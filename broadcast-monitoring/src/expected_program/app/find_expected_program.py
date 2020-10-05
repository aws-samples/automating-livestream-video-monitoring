# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from boto3.dynamodb.conditions import Key, Attr
import os
import sys
import logging

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.utils import query_item_ddb, convert_float_to_dec
from common.config import DDB_SCHEDULE_TABLE, LOG_LEVEL

logging.basicConfig()
logger = logging.getLogger('FindExpectedProgram')
logger.setLevel(LOG_LEVEL)


def find_expected_program_for_looping_input(stream_id, segment_start_time, duration_sec, ddb_client=None):
    """
    Find the expected program for the given video stream segment if the input is in looping
    (True live events will use a different approach by comparing absolute date time with program date time.
    :param stream_id: stream identifier
    :param segment_start_time: relative start timestamp of the video segment
    :param duration_sec: duration of video segment in seconds
    :param ddb_client: optional. a ddb client can be provided to overwrite the default client.
    :return: a dictionary of metadata about the expected program
        {
          "Team_Info": "MAN V TOT",
          "Station_Logo": "NBC",
          "Stream_ID": "test_1",
          "Event_Title": "MAN V TOT",
          "Event_ID": "SIM-EPL-002",
          "Event_Type": "Sports",
          "End_Time": 90.0,
          "Start_Time": 0.0,
          "languageCode": "en-en"
        }
    """
    loop_end_time = get_loop_end_time(stream_id, ddb_client)
    # because the expected program loops, use modulo operation to find the start time to look up in the schedule table
    # here we do math using Decimal to avoid floating point precision problems
    segment_start_time_in_loop = convert_float_to_dec(segment_start_time) % convert_float_to_dec(loop_end_time)
    logger.info(f'Loop input end time: {loop_end_time}, start time in loop: {segment_start_time_in_loop}')

    query_params = {
        'ScanIndexForward': True,
        'KeyConditionExpression': Key('Stream_ID').eq(stream_id) & Key('Start_Time').lte(
            segment_start_time_in_loop + convert_float_to_dec(duration_sec)),
        'FilterExpression': Attr('End_Time').gt(segment_start_time_in_loop)
    }

    # technically, it's possible one segment can straddle between two programs.
    # however, given segments is 6-10 seconds long, we will just take the first program
    items = query_item_ddb(DDB_SCHEDULE_TABLE, ddb_client, **query_params)
    expected_program = items[0]
    expected_program['Start_Time'] = float(expected_program['Start_Time'])
    expected_program['End_Time'] = float(expected_program['End_Time'])
    expected_program['Segment_Start_Time_In_Loop'] = float(segment_start_time_in_loop)
    logger.info(
        f'Found program title={expected_program["Event_Title"]} '
        f'({expected_program["Start_Time"]} - {expected_program["End_Time"]}) for video segment.')

    return expected_program


def get_loop_end_time(stream_id, ddb_client):
    """
    Look up the expected schedule to find the end timesteamp of the last program.
    This is useful when the input is a looping input.
    :param stream_id: stream identifier
    :param ddb_client: optional. a ddb client can be provided to overwrite the default client.
    :return:
    """
    query_params = {'ScanIndexForward': False,
                    'KeyConditionExpression': Key('Stream_ID').eq(stream_id),
                    'Limit': 1}
    items = query_item_ddb(DDB_SCHEDULE_TABLE, ddb_client, **query_params)
    latest_item = items[0]
    loop_end_time = float(latest_item['End_Time'])
    return loop_end_time


if __name__ == '__main__':
    find_expected_program_for_looping_input('test_1', 179, 3)
