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

from common.utils import check_enabled
from common.config import LOG_LEVEL, APPSYNC_NOTIFY_CONFIG_KEY

try:
    from .appsync_push_notification import push_appsync
except ImportError:
    from appsync_push_notification import push_appsync

logging.basicConfig()
logger = logging.getLogger('FindExpectedProgramMain')
logger.setLevel(LOG_LEVEL)


@check_enabled(APPSYNC_NOTIFY_CONFIG_KEY)
def lambda_handler(event, context):
    """
    :param event:
    {
      "s3Bucket": "aws-rnd-broadcast-maas-video-processing-precompute",
      "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
      "s3VersionId": "f78kDD1W9sL9f3bokb.7rzpZsz9WEQvD",
      "config": {
        "audio_check_enabled": true,
        "station_logo_check_enabled": true,
        "team_logo_check_enabled": false,
        "team_detect_check_enabled": false,
        "appsync_notify_enabled": true,
        "reuse_detection_if_available": true
      },
      "parsed": {
        "isMasterManifest": false,
        "streamId": "test_1",
        "lastSegment": {
          "s3Key": "live/test_video_single_pipeline/test_1_00031.ts",
          "versionId": "JmyirzTQ3pski.ByHQj8.FoPgUBDrwEo",
          "durationSec": 5,
          "startDateTime": "2020-03-05T18:49:28.708000Z",
          "startTimeRelative": 152.3
        },
        "expectedProgram": {
          "Station_Logo": "Good Logo",
          "Stream_ID": "test_1",
          "Event_Title": "news 1",
          "Event_ID": "SIM-PROG2",
          "Event_Type": "News",
          "End_Time": 180,
          "Start_Time": 90,
          "Segment_Start_Time_In_Loop": 152.3
        }
      },
      "reuse": {
        "enabled": true,
        "segment": "2020-03-05T18:07:19.792000Z"
      },
      "thumbnailKey": "frames/test_video_single_pipeline/test_1/resized/2020/03/05/18/00:24:792000.jpg",
      "statusSummary": {
        "Audio_Status": true,
        "Station_Status": false,
        "Team_Status": null
      }
    }
    :return:
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))
    segment_start_dt = event['parsed']['lastSegment']['startDateTime']
    segment_s3_key = event['parsed']['lastSegment']['s3Key']
    stream_id = event['parsed']['streamId']
    segment_duration = event['parsed']['lastSegment']['durationSec']

    thumbnail_s3_key = event['thumbnailKey']
    status_summary = event['statusSummary']

    # notify frontend new stream summary is available
    push_appsync(stream_id=stream_id,
                 segment_start_date_time_str=segment_start_dt,
                 segment_duration_sec=segment_duration,
                 segment_s3_key=segment_s3_key,
                 thumbnail_s3_key=thumbnail_s3_key,
                 media_check_status=status_summary
                 )
    return event
