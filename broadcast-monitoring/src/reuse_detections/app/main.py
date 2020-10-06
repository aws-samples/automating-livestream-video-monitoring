# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import json
import os
import sys
import copy
import time
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

# Conditionally add /opt to the PYTHON PATH
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.config import DDB_FRAME_TABLE, DDB_FRAGMENT_TABLE, LOG_LEVEL, UTC_TIME_FMT
from common.utils import get_item_ddb, DDBUpdateBuilder, query_item_ddb, put_item_ddb

logging.basicConfig()
logger = logging.getLogger('reuseDetections')
logger.setLevel(LOG_LEVEL)

REUSE_ITEM_TTL_HR = 24


def lambda_handler(event, context):
    logger.info('Received event: %s', json.dumps(event, indent=2))

    reuse_segment_start_dt = event['reuse']['segment']
    stream_id = event['parsed']['streamId']
    segment_start_dt = event['parsed']['lastSegment']['startDateTime']

    expire_ttl = int(time.time()) + REUSE_ITEM_TTL_HR * 60 * 60
    first_frame_thumbnail_key = reuse_frames(stream_id, reuse_segment_start_dt, segment_start_dt, expire_ttl)
    segment_status_summary = reuse_segment_detection(reuse_segment_start_dt, segment_start_dt, stream_id, expire_ttl)

    event['thumbnailKey'] = first_frame_thumbnail_key
    event['statusSummary'] = segment_status_summary
    return event


def reuse_frames(stream_id, reuse_segment_start_dt_str, segment_start_dt_str, expire_ttl):
    """
    Find frame analysis to reuse for the video segment, and copy the info to the rows for the new frames.
    :return The thumbnail key of the first frame
    """
    reuse_segment_id = f'{stream_id}:{reuse_segment_start_dt_str}'
    query_params = {
        'ScanIndexForward': True,
        'IndexName': 'Segment_Millis',
        'KeyConditionExpression': Key('Segment').eq(reuse_segment_id)
    }

    frame_detections_to_reuse = query_item_ddb(DDB_FRAME_TABLE, **query_params)
    logger.info(f'found {len(frame_detections_to_reuse)} frames to reuse detections')

    segment_id = f'{stream_id}:{segment_start_dt_str}'

    first_frame_thumbnail_key = None
    for frame_detection in frame_detections_to_reuse:
        frame_to_write = copy.deepcopy(frame_detection)
        frame_dt = datetime.strptime(segment_start_dt_str, UTC_TIME_FMT) + timedelta(
            milliseconds=float(frame_detection['Segment_Millis']))
        frame_to_write['DateTime'] = frame_dt.strftime(UTC_TIME_FMT)
        frame_to_write['Segment'] = segment_id
        frame_to_write['ExpireTTL'] = expire_ttl
        put_item_ddb(DDB_FRAME_TABLE, frame_to_write)
    if frame_detections_to_reuse:
        first_frame_thumbnail_key = frame_detections_to_reuse[0].get('Resized_S3_Key',
                                                                     frame_detections_to_reuse[0].get('S3_Key', None))
    return first_frame_thumbnail_key


def reuse_segment_detection(reuse_segment_start_dt, segment_start_dt, stream_id, expire_ttl):
    """
    Download the segment analysis to reuse, and copy the info to the new segment
    :return status summary for each check
    """
    segment_detection_to_reuse = get_item_ddb(Key={'Stream_ID': stream_id, 'Start_DateTime': reuse_segment_start_dt},
                                              table_name=DDB_FRAGMENT_TABLE)
    current_segment = get_item_ddb(Key={'Stream_ID': stream_id, 'Start_DateTime': segment_start_dt},
                                   table_name=DDB_FRAGMENT_TABLE)

    with DDBUpdateBuilder(
            key={'Start_DateTime': segment_start_dt, 'Stream_ID': stream_id},
            table_name=DDB_FRAGMENT_TABLE,
    ) as ddb_update_builder:
        # do not overwrite info that has already been written to the current segment entry
        detections = copy.deepcopy(segment_detection_to_reuse)
        for attr in current_segment.keys():
            detections.pop(attr, None)
        for attr in [key for key in detections.keys() if not key.startswith('Reused') and key != 'ExpireTTL']:
            ddb_update_builder.update_attr(attr, detections[attr])
        ddb_update_builder.update_attr('Reused_Detection', True)
        ddb_update_builder.update_attr('ExpireTTL', expire_ttl)
        ddb_update_builder.update_attr('Reused_From', detections.get('Reused_From', reuse_segment_start_dt))

    status_summary = {
        'Audio_Status': segment_detection_to_reuse.get('Audio_Status', None),
        'Station_Status': segment_detection_to_reuse.get('Station_Status', None),
        'Team_Status': segment_detection_to_reuse.get('Team_Status', None),
        'Sports_Status': segment_detection_to_reuse.get('Sports_Status', None)
    }
    logger.info(f'check status summary: {status_summary}')
    return status_summary
