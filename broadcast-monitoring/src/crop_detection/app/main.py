# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from PIL import Image

import os
import logging
import sys
import json

from io import BytesIO

# Conditionally add /opt to the PYTHON PATH for lambda layer
if os.getenv('AWS_EXECUTION_ENV') is not None:
    sys.path.append('/opt')

from common.utils import (from_s3_object, upload_file_to_s3, DDBUpdateBuilder, DecimalEncoder, check_enabled,
                          get_item_ddb, cleanup_dir)
from common.config import WORKING_DIR, LOG_LEVEL, DDB_FRAME_TABLE, STATION_LOGO_CHECK_CONFIG_KEY

logging.basicConfig()
logger = logging.getLogger('ImageCrop')
logger.setLevel(LOG_LEVEL)


def crop(bytes, bb, output_path):
    """
    Read in an image from bytes and given bounding box (Width, Height, Left, Top), crop the image and save to file.
    """
    image = Image.open(bytes)
    width, height = image.size
    left = bb['Left'] * width
    top = bb['Top'] * height
    right = bb['Width'] * width + left
    bottom = bb['Height'] * height + top
    cropped = image.crop((left, top, right, bottom))
    cropped.save(output_path)
    logger.info(f'Cropped image to {output_path}')


def crop_image_from_s3(src_s3_bucket, src_s3_key, bb, name, dst_s3_bucket=None, dst_s3_key=None):
    """
    Download image from s3, crop it by specified bounding box (Width, Height, Left, Top),
    then write the cropped image to s3
    """
    # use the same image file extension as the source image
    src_ext = os.path.splitext(src_s3_key)[1]
    output_path = os.path.join(WORKING_DIR, f'cropped{src_ext}')
    with BytesIO() as buf:
        crop(from_s3_object(src_s3_bucket, src_s3_key, buf), bb, output_path)
    if dst_s3_bucket is None:
        dst_s3_bucket = src_s3_bucket
    if dst_s3_key is None:
        dst_s3_key = f'{os.path.splitext(src_s3_key)[0]}_crop_{name}_{bb["Left"]:0.3f}_{bb["Top"]:0.3f}{src_ext}'
    upload_file_to_s3(dst_s3_bucket, dst_s3_key, output_path)
    return dst_s3_bucket, dst_s3_key


@cleanup_dir()
@check_enabled(STATION_LOGO_CHECK_CONFIG_KEY)
def crop_station_logo_lambda_handler(event, context):
    """
    This lambda function downloads the station logo detection results for the given frame (look up by S3 key) from DDB
    Crops the detected logo, saves it into S3 and update DDB with pointer to the cropped image.

    :param event: e.g.
    {
      "parsed": {
        ...
      },
      "config": {
        "station_logo_check_enabled": true,
        ...
      },
      "frame": {
        "Stream_ID": "test_1",
        "DateTime": "2020-02-22T22:14:53.375000Z",
        "Segment": "live/test_video_single_pipeline/test_1_00032.ts",
        "Segment_Millis": 0,
        "Segment_Frame_Num": 0,
        "S3_Bucket": "aws-rnd-broadcast-maas-video-processing-dev-crop",
        "S3_Key": "frames/test_video_single_pipeline/test_1/original/2020/02/22/22/14:53:375000.jpg",
        "Frame_Width": 1280,
        "Frame_Height": 720,
        "Resized_S3_Key": "frames/test_video_single_pipeline/test_1/resized/2020/02/22/22/14:53:375000.jpg"
      }
    }
    :return null
    """
    frame_s3_bucket = event['frame']['S3_Bucket']
    frame_s3_key = event['frame']['S3_Key']
    frame_table_key = {'Stream_ID': event['frame']['Stream_ID'], 'DateTime': event['frame']['DateTime']}
    # download detection
    item = get_item_ddb(table_name=DDB_FRAME_TABLE, Key=frame_table_key, AttributesToGet=['Detected_Station_Logos'])

    logo_detection_results = item.get('Detected_Station_Logos', [])
    if logo_detection_results:
        logger.info(logo_detection_results[0])
        bb = json.loads(json.dumps(logo_detection_results[0]['Geometry']['BoundingBox'], cls=DecimalEncoder))
        name = logo_detection_results[0]['Name']
        # crop image
        dst_s3_bucket, dst_s3_key = crop_image_from_s3(frame_s3_bucket, frame_s3_key, bb, name, dst_s3_bucket=None,
                                                       dst_s3_key=None)

        with DDBUpdateBuilder(key=frame_table_key, table_name=DDB_FRAME_TABLE) as update_builder:
            update_builder.update_attr('Detected_Station_Logo_Crop_S3_KEY', dst_s3_key)


if __name__ == '__main__':
    key = "frames/test_video_single_pipeline/test_1/original/2020/02/19/15/10:56:595500.jpg"
    bucket = "aws-rnd-broadcast-maas-video-processing-dev"
    bb = {
        "Width": 0.10493999719619751,
        "Height": 0.18562999367713928,
        "Left": 0.8615900278091431,
        "Top": 0.08986999839544296
    }

    crop_image_from_s3(bucket, key, bb, 'bad_logo')
