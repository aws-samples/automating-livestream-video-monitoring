# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import yaml
import os
import logging
import copy

logger = logging.getLogger("TeamInfo")


class Team(object):
    def __init__(self, name, abbreviations, alt_names=[], team_id=None):
        self.name = name
        self.abbreviations = abbreviations
        self.alt_names = alt_names
        self.team_id = team_id

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f'Name={self.name};' \
               f'Id={self.team_id};' \
               f'Abbreviations={self.abbreviations};' \
               f'AltNames={self.alt_names}'


class TeamInfoFactory(object):
    """
    Factory method that provides info about teams. It reads in yaml configuration to load team names and abbreviations.
    """

    def __init__(self):
        self.abbr_to_team = {}  # map of abbreviations -> Team object
        self.teams = {}  # map of team name -> Team object
        self.team_id_to_team = {}  # map of team id -> Team object
        team_info_yaml_file = os.path.dirname(os.path.realpath(__file__)) + '/data/teams.yaml'
        self.load_items_from_yaml(team_info_yaml_file)

    def load_items_from_yaml(self, item_yaml_file):
        try:
            with open(item_yaml_file, 'r') as f:
                items = yaml.safe_load(f)
                for team_name in items:
                    team_id = items[team_name]['id']
                    abbrs = items[team_name]['abbr']
                    alt_names = []
                    if 'alt' in items[team_name]:
                        alt_names = items[team_name]['alt']
                    team = Team(team_name, abbrs, alt_names, team_id)
                    self.teams[team_name] = team
                    self.team_id_to_team[team_id] = team
                    for abbr in abbrs:
                        if self.abbr_exists(abbr):
                            error_msg = f'found duplicate abbreviations: {abbr} for ' \
                                        f'{self.abbr_to_team[abbr].name} and {team_name}'
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        self.abbr_to_team[abbr] = team
                    for alt_name in alt_names:
                        self.teams[alt_name] = team
        except yaml.YAMLError as exc:
            logger.exception(str(exc))

    def abbr_exists(self, abbr):
        return abbr in self.abbr_to_team

    def team_exists(self, team_name):
        return bool(set(self.teams.keys()) & {team_name, team_name.lower()})

    def get_team_from_abbr(self, abbr):
        if self.abbr_exists(abbr):
            return copy.deepcopy(self.abbr_to_team[abbr])
        else:
            return None

    def get_team_from_id(self, team_id):
        if team_id in self.team_id_to_team:
            return self.team_id_to_team[team_id]
        else:
            return None

    def get_team(self, team_name):
        if self.team_exists(team_name):
            return copy.deepcopy(self.teams[team_name] if team_name in self.teams else self.teams[team_name.lower()])
        else:
            return None
