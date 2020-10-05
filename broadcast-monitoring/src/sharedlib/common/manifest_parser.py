# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from datetime import datetime, timedelta
import logging

"""
Helper functions that parses manifest files that looks like: 

#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:7
#EXT-X-MEDIA-SEQUENCE:1
#EXT-X-PROGRAM-DATE-TIME:2020-01-21T16:34:45.400Z
#EXTINF:6.00600,
test_1_00001.ts
#EXTINF:6.00600,
test_1_00002.ts
...

"""

from .config import LOG_LEVEL

logger = logging.getLogger('ManifestParser')
logger.setLevel(LOG_LEVEL)

UTC_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
PROGRAM_TIME_KEYWORD = '#EXT-X-PROGRAM-DATE-TIME:'
DURATION_KEYWORD = 'EXTINF:'
SEGMENT_SUFFIX = '.ts'


def get_last_segment_and_start_timestamp(manifest_content):
    """
    Parse the m3u8 manifest to retrieve the name of the last segment and its starting timestamp (absolute)
    :param manifest_content: content of the m3u8 manifest
    :return:
        segment: name of the last segment
        latest_segment_start_time: if EXT-X-PROGRAM-DATE-TIME is present in the manifest, the starting timestamp of
         the last segment
        duration_sec: duration of the last segments in seconds
    """
    manifest_lines = manifest_content.split('\n')
    latest_segment_duration = timedelta()
    segment_date_time = None
    segment = None
    for line in manifest_lines:
        if PROGRAM_TIME_KEYWORD in line:
            date_time_str = line.split(PROGRAM_TIME_KEYWORD)[-1]
            segment_date_time = datetime.strptime(date_time_str, UTC_TIME_FMT)
        if DURATION_KEYWORD in line:
            duration_sec = float(line.split(DURATION_KEYWORD)[-1].split(',')[0])
            latest_segment_duration = timedelta(seconds=duration_sec)
            if segment_date_time is not None:
                segment_date_time += latest_segment_duration
        if line.endswith(SEGMENT_SUFFIX):
            segment = line

    if segment_date_time is not None:
        # the segment duration occurs before the segment name, subtract the last segment duration to get the start time
        latest_segment_start_time = segment_date_time - latest_segment_duration
        return segment, latest_segment_start_time, duration_sec
    else:
        return segment, None, duration_sec


def is_master_manifest(manifest_content):
    """
    Parse the m3u8 manifest to see if this is the master manifest that points to other manifests.
    :param manifest_content:
    :return: True if it's the master manifest
    """
    manifest_lines = manifest_content.split('\n')
    for line in manifest_lines:
        if ".m3u" in line:
            return True
    return False
