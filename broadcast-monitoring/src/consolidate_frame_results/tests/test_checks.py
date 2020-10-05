import pytest
from pytest import approx

from ..app.checks import calculate_team_confidence


@pytest.mark.parametrize(
    'expected_status, expected_confidence, team_prefix, frame_data', [
        (
            True, 89.6, 'Team1', {
                'Team1_Text_Status': True,
                'Team1_Logo_Status': True,
                'Team1_Text_Detected': [{'Confidence': 92.0}],
                'Team1_Logo_Detected': [{'Confidence': 80.0}]
            }
        ),
        (
            True, 73.6, 'Team1', {
                'Team1_Text_Status': True,
                'Team1_Logo_Status': None,
                'Team1_Text_Detected': [{'Confidence': 92.0}],
                'Team1_Logo_Detected': None
            }
        ),
        (
            True, 72.0, 'Team1', {
                'Team1_Text_Status': None,
                'Team1_Logo_Status': True,
                'Team1_Text_Detected': [],
                'Team1_Logo_Detected': [{'Confidence': 90.0}]
            }
        ),
        (
            False, 0.0, 'Team1', {
                'Team1_Text_Status': None,
                'Team1_Logo_Status': None,
                'Team1_Text_Detected': [],
                'Team1_Logo_Detected': []
            }
        ),
        (
            False, 87.0, 'Team1', {
                'Team1_Text_Status': False,
                'Team1_Logo_Status': False,
                'Team1_Text_Detected': [{'Confidence': 90.0}],
                'Team1_Logo_Detected': [{'Confidence': 75.0}]
            }
        ),
        (
            False, 64.0, 'Team1', {
                'Team1_Text_Status': None,
                'Team1_Logo_Status': False,
                'Team1_Text_Detected': [],
                'Team1_Logo_Detected': [{'Confidence': 80.0}]
            }
        ),
        (
            False, 65.0, 'Team1', {
                'Team1_Text_Status': False,
                'Team1_Logo_Status': None,
                'Team1_Text_Detected': [{'Confidence': 81.25}],
                'Team1_Logo_Detected': []
            }
        ),
        (
            False, 10.0, 'Team1', {
                'Team1_Text_Status': True,
                'Team1_Logo_Status': False,
                'Team1_Text_Detected': [{'confidence': 90.0}],
                'Team1_Logo_Detected': [{'confidence': 80.0}]
            }
        ),
        (
            False, 17.0, 'Team1', {
                'Team1_Text_Status': False,
                'Team1_Logo_Status': True,
                'Team1_Text_Detected': [{'Confidence': 80.0}],
                'Team1_Logo_Detected': [{'Confidence': 97.0}]
            }
        ),
    ])
def test_calculate_team_results(team_prefix, frame_data, expected_status, expected_confidence):

    res = dict(calculate_team_confidence(team_prefix, frame_data))

    assert expected_status == res['Team1_Status']
    assert expected_confidence == approx(res['Team1_Detection_Confidence'], 0.01)
