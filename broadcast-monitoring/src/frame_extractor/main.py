import os
import logging
import json
# layers
import sys

sys.path.append('/opt')

from common.utils import download_file_from_s3, parse_date_time_from_str, cleanup_dir
from common.config import LOG_LEVEL, S3_BUCKET, FRAME_SAMPLE_FPS

from frame_extractor import extract_frames

logging.basicConfig()
logger = logging.getLogger('FrameExtractor')
logger.setLevel(LOG_LEVEL)


@cleanup_dir()
def lambda_handler(event, context):
    """
    Download the video segment and sample frames from it. Upload each extracted frame and store the metadata
    :param event: example
    {
      "s3Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
      "s3Key": "live/test_video_single_pipeline/test_1.m3u8",
      "s3VersionId": "KJCfz6c8Il5E_23jbzwYuFhGIpvMnrJE",
      "parsed": {
        {
            "isMasterManifest": false,
            "streamId": "test_1",
            "lastSegment": {
                "s3Key": "live/test_video_single_pipeline/test_1_00039.ts",
                "startDateTime": "2020-01-23T21:36:35.290000Z",
                "durationSec": 6
            },
            "expectedProgram"{
                ...
            }
        }
      }
    }
    :param context: lambda context object https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    :return: A list of extracted frames metadata. e.g.
    [
      {
        "Stream_ID": "test_1",
        "DateTime": "2020-01-23T21:36:35.290000Z",
        "Chunk": "test_1_00016.ts",
        "Millis_In_Chunk": 0,
        "Frame_Num": 0,
        "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev",
        "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/01/23/21/36:35:290000.jpg"
      },
      ...
    ]
    """
    logger.info('Received event: %s', json.dumps(event, indent=2))
    manifest_s3_key = event['s3Key']
    manifest_s3_bucket = event['s3Bucket']
    segment_s3_key = event['parsed']['lastSegment']['s3Key']
    starting_time_str = event['parsed']['lastSegment']['startDateTime']
    starting_time = parse_date_time_from_str(starting_time_str)
    stream_id = event['parsed']['streamId']
    # the cleanup_dir decorator will ensure the tmp/ working directory gets cleaned up if lambda container is reused
    segment_file = download_file_from_s3(manifest_s3_bucket, segment_s3_key)
    frame_s3_prefix = os.path.splitext(manifest_s3_key.replace('live', 'frames'))[0]
    logger.info(f'S3 prefix for extracted frames: {frame_s3_prefix}')
    frames = extract_frames(stream_id, segment_s3_key, segment_file, starting_time, S3_BUCKET, frame_s3_prefix,
                            FRAME_SAMPLE_FPS)
    return frames
