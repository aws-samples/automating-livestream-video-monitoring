# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import json
import os
import sys

# Conditionally add /opt to the PYTHON PATH
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from audio_detect import execute_ffmpeg
from common.utils import download_file_from_s3, check_enabled, cleanup_dir
from common.config import LOG_LEVEL

logging.basicConfig()
logger = logging.getLogger('AudioDetection')
logger.setLevel(LOG_LEVEL)

SILENCE_THRESHOLD = os.getenv('SILENCE_THRESHOLD', '-60dB')
SILENCE_DURATION = os.getenv('SILENCE_DURATION', 1)


@check_enabled("audio_check_enabled")
@cleanup_dir()
def lambda_handler(event, context):
    """Download a transport stream file and process the audio to detect
    silence and the mean volume
    :param event:
    {
      "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
      "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
      "s3VersionId": "KJCfz6c8Il5E_23jbzwYuFhGIpvMnrJE",
      "parsed": {
        {
            "isMasterManifest": false,
            "streamId": "test_1",
            "lastSegment": {
                "s3Key": "live/test_video_single_pipeline/test_1_00039.ts", # only if isMasterManifest = false
                "startDateTime": "2020-01-23T21:36:35.290000Z",      # only returned if isMasterManifest = false
                "durationSec": 6
            },
            "expectedProgram"{
                ...
            }
        }
      }
    }
    :param context: lambda context object
    :return: A dict with representations of volume and silence chunks
    {
      "volume": {
        "mean": -22.0,
        "max": -4.3
      },
      "silence_chunks": [
        { "start": 1.33494, "end": 1.84523 },
        { "start": 3.52498, "end": 3.85456 }
      ]
    }
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))

    s3_bucket = event['s3Bucket']
    segment_s3_key = event['parsed']['lastSegment']['s3Key']

    # the cleanup_dir decorator will ensure the tmp/ working directory gets cleaned up if lambda container is reused
    input_stream = download_file_from_s3(s3_bucket, segment_s3_key)

    raw_results = execute_ffmpeg(
        input_stream, threshold=SILENCE_THRESHOLD, duration=SILENCE_DURATION
    )

    logger.info(f'raw results:{raw_results}')

    results = {
        'silence_chunks': [convert_silence_to_dict(seg) for seg in raw_results['silencedetect']]
    }
    if raw_results['volumedetect']:
        results['volume'] = convert_volume_to_dict(raw_results['volumedetect'])

    return results


def convert_volume_to_dict(vol):
    mean_vol, max_vol = vol
    return {'mean': mean_vol, 'max': max_vol}


def convert_silence_to_dict(silence):
    start, end = silence
    return {'start': start, 'end': end}
