# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging

from functools import wraps, partial
from operator import sub

from common.config import (
    LOG_LEVEL, STATION_LOGO_CHECK_CONFIG_KEY, TEAM_CHECK_CONFIG_KEY, STATION_LOGO_THRESHOLD,
    TEAM_LOGO_CHECK_CONFIG_KEY, TEAM_TEXT_SEGMENT_THRESHOLD, SPORTS_CHECK_CONFIG_KEY, SPORTS_TYPE_SEGMENT_THRESHOLD
)

logging.basicConfig()
logger = logging.getLogger('consolidate-checks')
logger.setLevel(LOG_LEVEL)


def check_attributes(*args):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.ddb_attrs = args
        return wrapper

    return inner


def add_check_attr(*checks):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.config_names = checks
        return wrapper

    return inner


@add_check_attr(STATION_LOGO_CHECK_CONFIG_KEY)
@check_attributes('Is_Expected_Logo', 'Logo_Detect_Error')
def station_logo_check(frames):
    frames_with_logo = [el['Is_Expected_Logo'] for el in frames if 'Is_Expected_Logo' in el]

    if not frames_with_logo:
        logger.info('No frames with logo result')
        return []

    detected_percent = (frames_with_logo.count(True) / len(frames_with_logo)) * 100
    yield 'Station_Status', detected_percent >= STATION_LOGO_THRESHOLD

    throttled_frames = [el for el in frames if 'Logo_Detect_Error' in el]
    if len(throttled_frames) > 0:
        yield 'Has_Logo_Detect_Error', True


def team_check_results(frame_data):
    status_keys = {'Team1_Status', 'Team2_Status'}
    status = {key: [frame[key] for frame in frame_data if key in frame] for key in status_keys}
    return status


@add_check_attr(TEAM_CHECK_CONFIG_KEY)
@check_attributes('Team1_Status', 'Team2_Status')
def team_text_check(frames):
    with_team_checks = team_check_results(frames)

    if not with_team_checks:
        logger.info('No frames with team text check')
        return

    check_statuses = []
    for k, checks in with_team_checks.items():
        if len(checks) > 0:
            detected_percent = (checks.count(True) / len(checks)) * 100
            check_status = detected_percent >= TEAM_TEXT_SEGMENT_THRESHOLD
            check_statuses.append(check_status)
            logger.info(f'{k} status: {check_status} ({detected_percent} %).')
    if check_statuses:
        team_status = True
        for check_status in check_statuses:
            team_status &= check_status
    else:
        team_status = False
    logger.info(f'Team_Status: {team_status}')
    yield 'Team_Status', team_status


@add_check_attr(SPORTS_CHECK_CONFIG_KEY)
@check_attributes('Sports_Status')
def sports_check(frames):
    sport_statuses = [el['Sports_Status'] for el in frames if 'Sports_Status' in el]

    if not sport_statuses:
        logger.info('No frames with sport check status')
        return

    detected_percent = (sport_statuses.count(True) / len(sport_statuses)) * 100
    check_status = detected_percent >= SPORTS_TYPE_SEGMENT_THRESHOLD
    logger.info(f'Sports_Status: {check_status}')
    yield 'Sports_Status', check_status


def get_confidence(key, data):
    res = data.get(key)

    if res is None:
        return res
    try:
        return max([el['Confidence'] for el in res], default=0.0)
    except KeyError:
        return max([el['confidence'] for el in res], default=0.0)


def calc_combined_confidence(text_confidence, logo_confidence, text_coef=0.0, logo_coef=0.0):
    if logo_confidence is None:
        logo_confidence = 0.0
    if text_confidence is None:
        text_confidence = 0.0

    return text_coef * text_confidence + logo_coef * logo_confidence


status_results = {
    (True, True): (True, partial(calc_combined_confidence, text_coef=0.8, logo_coef=0.2)),
    (True, None): (True, partial(calc_combined_confidence, text_coef=0.8)),
    (None, True): (True, partial(calc_combined_confidence, logo_coef=0.8)),
    (None, None): (False, partial(calc_combined_confidence)),
    (False, False): (False, partial(calc_combined_confidence, text_coef=0.8, logo_coef=0.2)),
    (False, None): (False, partial(calc_combined_confidence, text_coef=0.8)),
    (None, False): (False, partial(calc_combined_confidence, logo_coef=0.8)),
    (False, True): (False, sub),
    (True, False): (False, sub)
}


@add_check_attr(TEAM_CHECK_CONFIG_KEY, TEAM_LOGO_CHECK_CONFIG_KEY)
@check_attributes(
    'Team1_Text_Status', 'Team1_Text_Detected',
    'Team2_Text_Status', 'Team2_Text_Detected',
    'Team1_Logo_Status', 'Team1_Logo_Detected',
    'Team2_Logo_Status', 'Team2_Logo_Detected',
)  # yapf: disable
def calculate_team_confidence(team_prefix, frame_data):
    text_status = frame_data.get(f'{team_prefix}_Text_Status')
    logo_status = frame_data.get(f'{team_prefix}_Logo_Status')

    status, calc_confidence = status_results[(text_status, logo_status)]

    text_confidence = get_confidence(f'{team_prefix}_Text_Detected', frame_data)
    logo_confidence = get_confidence(f'{team_prefix}_Logo_Detected', frame_data)

    yield f'{team_prefix}_Status', status
    yield f'{team_prefix}_Detection_Confidence', abs(calc_confidence(text_confidence, logo_confidence))
