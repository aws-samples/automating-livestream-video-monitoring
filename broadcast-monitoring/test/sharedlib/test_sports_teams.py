from unittest import TestCase
import os
from sports_data.team import TeamInfoFactory

TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


class TestTeams(TestCase):
    def test_team_info(self):
        team_info = TeamInfoFactory()
        self.assertTrue(team_info.abbr_exists('LIV'))
        self.assertTrue(team_info.team_exists('Manchester United'))
        self.assertFalse(team_info.team_exists('Chicago Bears'))

        team_mu = team_info.get_team_from_abbr('MU')
        team_manchester_utd = team_info.get_team('Manchester Utd')
        self.assertEqual(team_mu, team_manchester_utd)

        with self.assertRaises(ValueError) as context:
            team_info.load_items_from_yaml(os.path.join(TEST_DATA_DIR, 'test_team_info.yaml'))
        self.assertTrue('duplicate abbreviations' in str(context.exception))
