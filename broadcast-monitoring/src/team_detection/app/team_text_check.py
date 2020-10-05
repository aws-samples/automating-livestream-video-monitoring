# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
from collections import defaultdict, deque
from decimal import Decimal
import json
from common.config import LOG_LEVEL
from common.utils import convert_dict_float_to_dec, parse_expected_teams, DecimalEncoder
from sports_data.team import TeamInfoFactory

logging.basicConfig()
logger = logging.getLogger('team-text-check')
logger.setLevel(LOG_LEVEL)


class TeamCheck:
    def __init__(self):
        self.ddb_attrs = ['Detected_Words']

    def execute(self, expected, data):

        team_info = TeamInfoFactory()
        expected_teams = parse_expected_teams(team_info, expected.get('Team_Info'))
        expected_teams.sort(key=lambda t: t.team_id)

        if expected_teams is None:
            logger.info('Expected Team Info not found')
            return

        expected_team_names = [team.name for team in expected_teams]
        detected_team_info = detect_team_from_text_in_image(team_info, data)

        result = {'Expected_Teams': expected_team_names, 'Detected_Teams': detected_team_info}

        # determine all keys in the detected teams dict that do NOT correspond with the
        # expected teams
        expected_ids = [team.team_id for team in expected_teams]
        non_matching_team_ids = [key for key in detected_team_info.keys() if key not in expected_ids]
        non_matching_team_ids.sort()
        logger.info(f'expected: {expected_ids}; found teams not expected: {non_matching_team_ids}')
        non_matching_team_ids = deque(non_matching_team_ids)

        for i, team in enumerate(expected_teams, 1):
            prefix = f'Team{i}_Text'
            result[f'{prefix}_Expected'] = {'id': team.team_id, 'name': team.name}
            expected_team_detected = detected_team_info.get(team.team_id)

            # the team_ids from the expected teams match the keys of the detections
            if expected_team_detected is not None:
                logger.info(f'Found expected team: {team.team_id}')
                result[f'{prefix}_Detected'] = expected_team_detected
                result[f'{prefix}_Status'] = True
            elif non_matching_team_ids:
                # team logos not matching the expected team were detected. This is a hard false
                result[f'{prefix}_Status'] = False
                non_matching_team = detected_team_info.get(non_matching_team_ids.popleft())
                result[f'{prefix}_Detected'] = non_matching_team
                logger.info(f'Found {non_matching_team} instead of team {team.team_id}')
            else:
                # when no text is detected, omit this attr.  This is an implicit None
                logger.info('No text status decided for Team%d - %s', i, team.name)

        return result


def detect_team_from_text_in_image(team_info, detected_words):
    """
    :param detected_text_response: see https://docs.aws.amazon.com/rekognition/latest/dg/API_DetectText.html
    [
      {
         "Confidence": number,
         "DetectedText": "string",
         "Geometry": {
            "BoundingBox": {
               "Height": number,
               "Left": number,
               "Top": number,
               "Width": number
            },
            "Polygon": [
               {
                  "X": number,
                  "Y": number
               }
            ]
         },
         "Id": number,
         "ParentId": number,
         "Type": "string"
      },
      ...
    ]
    :return: {
      "team_id": [
        {
          "id": "string",
          "name": "string",
          "text_detected": "string",
          "confidence": Decimal,
          "bb": {
            "Width": Decimal,
            "Height": Decimal,
            "Left": Decimal,
            "Top": Decimal
          }
        }
      ],
      ...
    }
    """
    teams_found = defaultdict(list)

    for result in [el for el in detected_words if el['Type'] == 'WORD']:
        detected_text = result['DetectedText']

        team_found = None

        if team_info.abbr_exists(detected_text):
            team_found = team_info.get_team_from_abbr(detected_text)
        elif team_info.team_exists(detected_text.lower()):
            team_found = team_info.get_team(detected_text.lower())

        if team_found is not None:
            logger.info(f'found team: {team_found.name} from text: {detected_text}')

            teams_found[team_found.team_id].append({
                'id': team_found.team_id,
                'name': team_found.name,
                'text_detected': detected_text,
                'confidence': Decimal(str(result['Confidence'])),
                'bb': convert_dict_float_to_dec(result['Geometry']['BoundingBox'])
            })
    logger.info(json.dumps(teams_found, indent=2, cls=DecimalEncoder))
    return teams_found
