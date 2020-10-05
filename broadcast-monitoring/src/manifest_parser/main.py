# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import json
import os
# layers
import sys

sys.path.append('/opt')
from common.config import LOG_LEVEL, DDB_FRAGMENT_TABLE
from common.manifest_parser import is_master_manifest, get_last_segment_and_start_timestamp
from common.utils import get_s3_object_latest_version_id, read_file_from_s3_w_versionid, parse_date_time_to_str, \
    put_item_ddb, convert_float_to_dec

logging.basicConfig()
logger = logging.getLogger('ManifestParser')
logger.setLevel(LOG_LEVEL)


def lambda_handler(event, context):
    """
    Download the playlist manifest file. Determine if it's the master manifest, and if it's child manifest,
     find the latest segment and calculate its starting date time using metadata in the manifest file.
    :param event: example
    {
        "Execution" : "arn:aws:states:us-east-1:12312312312:execution:statemachine-name:exc-id
        "Input": {
          "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
          "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
          "s3VersionId": "T.Lfm.fslzaZa5lkV_bJrI.MmrQG7mE_"
        }
    }
    :param context: lambda context object https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    :return: whether this is a master manifest. If it's child manifest, find the latest segment and starting date time.
    {
        "isMasterManifest": false,
        "streamId": "test_1",
        "lastSegment": { # only if isMasterManifest = false
            "s3Key": "live/test_video_single_pipeline/test_1_00039.ts",
            "startDateTime": "2020-01-23T21:36:35.290000Z",
            "durationSec": 6
        }
    }
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))
    s3_bucket = event['Input']['s3Bucket']
    manifest_s3_key = event['Input']['s3Key']
    manifest_s3_version_id = event['Input']['s3VersionId']

    manifest_content = read_file_from_s3_w_versionid(s3_bucket, manifest_s3_key, manifest_s3_version_id)
    if is_master_manifest(manifest_content):
        logger.info('Is master manifest. Skip processing')
        return {'isMasterManifest': True}
    else:
        last_segment, starting_time, duration_sec = get_last_segment_and_start_timestamp(manifest_content)
        segment_s3_key = os.path.join(os.path.dirname(manifest_s3_key), last_segment)
        segment_s3_version_id = get_s3_object_latest_version_id(s3_bucket, segment_s3_key)
        stream_id = os.path.splitext(os.path.basename(manifest_s3_key))[0]
        starting_time_str = parse_date_time_to_str(starting_time)

        fragment_ddb_entry = {
            'SFNArn': event['Execution'],
            'Stream_ID': stream_id,
            'Start_DateTime': starting_time_str,
            'S3_Key': segment_s3_key,
            'S3_VersionID': segment_s3_version_id,
            'Duration_Sec': convert_float_to_dec(duration_sec)
        }
        put_item_ddb(DDB_FRAGMENT_TABLE, fragment_ddb_entry)

        result = {'isMasterManifest': False,
                  'streamId': stream_id,
                  'lastSegment': {
                      's3Key': segment_s3_key,
                      'versionId': segment_s3_version_id,
                      'durationSec': duration_sec,
                      "startDateTime": starting_time_str}
                  }
        logger.info('Response : %s', json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    data = {
        "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
        "s3VersionId": "fkwneLJAQON90Hoynq5TCGm3owUfRGnw"
    }
    response = lambda_handler(data, None)
    print(response)
