# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
import json
from collections import defaultdict, deque


from common.config import LOG_LEVEL
from common.utils import parse_expected_teams
from sports_data.team import TeamInfoFactory

logging.basicConfig()
logger = logging.getLogger('team-logo-check')
logger.setLevel(LOG_LEVEL)


class TeamLogoCheck:
    def execute(self, expected_program_info, detected_logos):
        """
        Compare the detected logos against the names of the expected teams
        return the matching detecttions


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
              "Name": "aston_villa",
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
        team_info = TeamInfoFactory()
        expected_teams = parse_expected_teams(team_info, expected_program_info.get('Team_Info'))
        expected_teams.sort(key=lambda t: t.team_id)

        if expected_teams is None:
            logger.info('Expected Team Info not found')
            return

        logo_detections = defaultdict(list)
        for detection in detected_logos:
            detected_team = team_info.get_team_from_id(detection['Name'])
            if detected_team is None:
                logger.info(f'found no team matching id: {detection["Name"]}')
                continue
            detection['name'] = detected_team.name
            detection['id'] = detected_team.team_id
            del detection['Name']
            logo_detections[detected_team.team_id].append(detection)
        logger.info(f'team logo detected: {json.dumps(logo_detections, indent=2)}')

        # determine all keys in the detected logos dict that do NOT correspond with the
        # expected teams
        expected_ids = [team.team_id for team in expected_teams]
        non_matching_team_ids = [key for key in logo_detections.keys() if key not in expected_ids]
        non_matching_team_ids.sort()
        logger.info(f'expected: {expected_ids}; found teams not expected: {non_matching_team_ids}')
        non_matching_team_ids = deque(non_matching_team_ids)

        for i, team in enumerate(expected_teams, 1):
            team_logo_detections = logo_detections.get(team.team_id)
            prefix = f'Team{i}_Logo'

            # when no logo detections are found for the expected team, use the remaining detections
            # for the "non" expected teams...these are True Negatives
            if team_logo_detections is None:
                logger.info('No logos detected for team id: %s', team.team_id)
                if non_matching_team_ids:
                    team_logo_detections = logo_detections.get(non_matching_team_ids.popleft())
                    logger.info(f'Found {team_logo_detections} instead')
                else:
                    team_logo_detections = []
            yield f'{prefix}_Expected', {'id': team.team_id, 'name': team.name}
            yield f'{prefix}_Detected', team_logo_detections

            confidence = max([det['Confidence'] for det in team_logo_detections]) if team_logo_detections else 0
            yield f'{prefix}_Confidence', confidence

            # test the team_ids from the expected teams match the keys of the detections
            if team.team_id in logo_detections:
                yield f'{prefix}_Status', True
            elif team_logo_detections:
                # team logos not matching the expected team were detected. This is a hard false
                yield f'{prefix}_Status', False
            else:
                # when no logo status is detected, omit this attr.  This is an implicit None
                logger.info('No Logo status decided for Team%d - %s', i, team.name)
