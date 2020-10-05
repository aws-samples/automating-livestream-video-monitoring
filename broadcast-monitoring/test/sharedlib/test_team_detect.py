from common.utils import parse_expected_teams
from sports_data.team import TeamInfoFactory


def test_parse_expected_teams():
    team_info = TeamInfoFactory()

    def team_names(teams):
        return [t.name for t in teams]

    teams = parse_expected_teams(team_info, 'AVL V NOR')
    assert team_names(teams) == ['Aston Villa', 'Norwich City']

    teams = parse_expected_teams(team_info, 'BOU V ARS')
    assert team_names(teams) == ['AFC Bournemouth', 'Arsenal']
