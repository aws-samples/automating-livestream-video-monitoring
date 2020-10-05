# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
S3_BUCKET = os.getenv('S3_BUCKET', 'aws-rnd-broadcast-maas-video-processing-dev')
WORKING_DIR = os.getenv('WORKING_DIR', '/tmp/')

#################################
# Check feature flags
#################################
STATION_LOGO_CHECK_CONFIG_KEY = 'station_logo_check_enabled'
TEAM_CHECK_CONFIG_KEY = 'team_detect_check_enabled'
TEAM_LOGO_CHECK_CONFIG_KEY = 'team_logo_check_enabled'
SPORTS_CHECK_CONFIG_KEY = 'sports_detect_check_enabled'
APPSYNC_NOTIFY_CONFIG_KEY = 'appsync_notify_enabled'
REUSE_DETECTION_CONFIG_KEY = 'reuse_detection_if_available'

#################################
# Frame extraction configurations
#################################

STORE_FRAMES = os.getenv("STORE_FRAMES", "all")
FRAME_RESIZE_WIDTH = int(os.getenv("FRAME_RESIZE_WIDTH", 256))
FRAME_RESIZE_HEIGHT = int(os.getenv("FRAME_RESIZE_HEIGHT", 144))
# consider make this a dynamic configuration based on the program
FRAME_SAMPLE_FPS = float(os.getenv("FRAME_SAMPLE_FPS", 1))
DDB_FRAME_TABLE = os.getenv('DDB_FRAME_TABLE', 'video-processing-dev-VideoFrames')
DDB_FRAGMENT_TABLE = os.getenv('DDB_FRAGMENT_TABLE', 'video-processing-dev-Segments')
DDB_SCHEDULE_TABLE = os.getenv('DDB_SCHEDULE_TABLE', 'video-processing-dev-Schedule')

#################################
# Frame extraction configurations
#################################
STATION_LOGO_THRESHOLD = float(os.getenv('STATION_LOGO_THRESHOLD', 75))
TEAM_TEXT_SEGMENT_THRESHOLD = float(os.getenv('TEAM_TEXT_SEGMENT_THRESHOLD', 75))
SPORTS_TYPE_SEGMENT_THRESHOLD = float(os.getenv('SPORTS_TYPE_SEGMENT_THRESHOLD', 50))

#################################
# Timestamp
#################################
UTC_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

#################################
# Result Evaluation
#################################

#################################
# Appsync notifications
#################################
APPSYNC_API_KEY = os.getenv('APPSYNC_API_KEY')
APPSYNC_API_ENDPOINT_URL = os.getenv('APPSYNC_API_ENDPOINT_URL')
