import logging
import os
from datetime import timedelta
# layers
import sys

sys.path.append('/opt')

import cv2
from common.config import LOG_LEVEL, FRAME_RESIZE_WIDTH, FRAME_RESIZE_HEIGHT, STORE_FRAMES, \
    DDB_FRAME_TABLE, UTC_TIME_FMT
from common.utils import upload_to_s3, put_item_ddb

logger = logging.getLogger('FrameExtractor')
logger.setLevel(LOG_LEVEL)

S3_KEY_DATE_FMT = "%Y/%m/%d/%H/%M:%S:%f"


def extract_frames(stream_id, segment_s3_key, video_chunk, video_start_datetime, s3_bucket, frame_s3_prefix,
                   sample_fps=1):
    if STORE_FRAMES not in ["all", "original", "resized"]:
        raise ValueError(f'Invalid STORE_FRAMES option: {STORE_FRAMES} (Valid: all, original, resized)')

    store_original_frames = STORE_FRAMES in ["all", "original"]
    store_resized_frames = STORE_FRAMES in ["all", "resized"]
    logger.info(f'Store original sized frame? {store_original_frames}, Store resized frames? {store_resized_frames}')

    cap = cv2.VideoCapture(video_chunk)
    extracted_frames_metadata = []
    try:
        video_metadata = extract_video_metadata(cap)

        hop = round(video_metadata['fps'] / sample_fps)
        if hop == 0:
            hop = 1  # if sample_fps is invalid extract every frame
        logger.info(f'Extracting every {hop} frame.')

        frame_count = 0
        extracted_frames = 0
        while cap.isOpened():
            success, frame = cap.read()
            if success:
                if frame_count % hop == 0:
                    # timestamp relative to start of video
                    frame_timestamp_millis = cap.get(cv2.CAP_PROP_POS_MSEC)
                    # absolute timestamp of the frame
                    frame_datetime = video_start_datetime + timedelta(milliseconds=frame_timestamp_millis)
                    segment_id = f'{stream_id}:{video_start_datetime.strftime(UTC_TIME_FMT)}'
                    frame_metadata = {'Stream_ID': stream_id,
                                      'DateTime': frame_datetime.strftime(UTC_TIME_FMT),
                                      'Segment': segment_id,
                                      'Segment_Millis': int(frame_timestamp_millis),
                                      'Segment_Frame_Num': frame_count,
                                      'S3_Bucket': s3_bucket}
                    if store_original_frames:
                        jpg = cv2.imencode(".jpg", frame)[1]
                        # use absolute timestamps for s3 key. might be easier to reason about.
                        frame_key = os.path.join(frame_s3_prefix, 'original',
                                                 f'{frame_datetime.strftime(S3_KEY_DATE_FMT)}.jpg')
                        # TODO: Should we also store the frame metadata in the s3 object?
                        s3_object_metadata = {'ContentType': 'image/jpeg'}
                        upload_to_s3(s3_bucket, frame_key, bytearray(jpg), **s3_object_metadata)
                        frame_metadata['S3_Key'] = frame_key
                        frame_metadata['Frame_Width'] = int(video_metadata['original_frame_width'])
                        frame_metadata['Frame_Height'] = int(video_metadata['original_frame_height'])
                    if store_resized_frames:
                        resized_frame = cv2.resize(frame, (FRAME_RESIZE_WIDTH, FRAME_RESIZE_HEIGHT))
                        resized_jpg = cv2.imencode(".jpg", resized_frame)[1]
                        # use absolute timestamps for s3 key. might be easier to reason about.
                        resized_frame_key = os.path.join(frame_s3_prefix, 'resized',
                                                         f'{frame_datetime.strftime(S3_KEY_DATE_FMT)}.jpg')
                        s3_object_metadata = {'ContentType': 'image/jpeg'}
                        upload_to_s3(s3_bucket, resized_frame_key, bytearray(resized_jpg), **s3_object_metadata)
                        if 'S3_Key' in frame_metadata:
                            frame_metadata['Resized_S3_Key'] = resized_frame_key
                        else:
                            frame_metadata['S3_Key'] = frame_key
                            frame_metadata['Frame_Width'] = FRAME_RESIZE_WIDTH
                            frame_metadata['Frame_Height'] = FRAME_RESIZE_HEIGHT
                    # persist frame metadata in database
                    put_item_ddb(DDB_FRAME_TABLE, frame_metadata)
                    extracted_frames_metadata.append(frame_metadata)
                    extracted_frames += 1
                frame_count += 1
            else:
                break
        logger.info(f'Extracted {extracted_frames} out of {frame_count} frames from {video_chunk}')
        return extracted_frames_metadata
    finally:
        cv2.destroyAllWindows()
        cap.release()


def extract_video_metadata(cap):
    metadata = {
        'original_frame_width': cap.get(cv2.CAP_PROP_FRAME_WIDTH),
        'original_frame_height': cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
        'fourcc': cap.get(cv2.CAP_PROP_FOURCC),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'format': cap.get(cv2.CAP_PROP_FORMAT),
        'mode': cap.get(cv2.CAP_PROP_MODE),
        'fps': cap.get(cv2.CAP_PROP_FPS),
    }
    logger.info(f'video metadata: {metadata}')
    return metadata
