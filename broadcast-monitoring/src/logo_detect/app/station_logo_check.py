# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from pathlib import Path
import logging

import yaml

from common.config import LOG_LEVEL

STATION_LOGO_DETECT_CHECK = 'station_logo_check_enabled'

logging.basicConfig()
logger = logging.getLogger('station-logo-check')
logger.setLevel(LOG_LEVEL)


class StationLogoCheck:
    def __init__(self, file_name='data/stations.yaml'):
        self.station_file = Path(__file__).parent.joinpath(file_name)
        self.station_data = self.load_station_data(self.station_file)
        self.station_names_logos_map = self.load_station_name_to_logos()
        self.station_logos_to_name_map = self.load_station_logos_to_name()
        self.ddb_attrs = ['Detected_Station_Logos']

    def load_station_data(self, file_name):
        try:
            with open(file_name, 'r') as f:
                data = yaml.safe_load(f)

        except Exception as e:
            raise e
        else:
            return data

    def load_station_name_to_logos(self):
        return {name: set(v['logos']) for v in self.station_data.values() for name in v['names']}

    def load_station_logos_to_name(self):
        return {logo: v['names'][0] for v in self.station_data.values() for logo in v['logos']}

    def execute(self, expected_program_info, detected_logos):
        """
        Execute the station check comparing the detected logo against a set of expected logos
        determined from the station name

        :param expected: Expected Program data
        {
            "Team_Info": "AVL V NOR",
            "Station_Logo": "Prime Video",
                ...
            "Start_Time": 180,
            "languageCode": "en-en",
            "Segment_Start_Time_In_Loop": 189.9875
        }
        :param data:
          [
            {
              "Name": "",
              "Confidence": 88.0790023803711,
              "Geometry": {
                "BoundingBox": {
                  "Width": 0.03180000185966492,
                  "Height": 0.07208999991416931,
                  "Left": 0.23874999582767487,
                  "Top": 0.2536500096321106
                }
              }
            },
            ...
          ]
        """
        expected_station = expected_program_info.get('Station_Logo')

        if expected_station not in self.station_names_logos_map:
            logger.info('Expected Station Logo not found: %s', expected_station)
            return

        yield 'Detected_Station_Logos', detected_logos

        logo_match = False
        try:
            detected_logo_name = detected_logos[0]['Name']
            logo_match = detected_logo_name in self.station_names_logos_map[expected_station]
            detected_station_name = self.station_logos_to_name_map[detected_logo_name]
            yield 'Detected_Logo', detected_station_name
            yield 'Detected_Logo_Confidence', detected_logos[0]['Confidence']
        except IndexError:
            logger.info('No detected logos found for frame')
            yield 'Detected_Logo', None

        yield 'Expected_Logo', expected_station
        yield 'Is_Expected_Logo', logo_match
