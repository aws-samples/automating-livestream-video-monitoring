import pytest
from ..app.team_logo_check import TeamLogoCheck


@pytest.fixture
def detected_logos():
    return [{
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
    }, {
        "Name": "norwich_city",
        "Confidence": 78.0790023803711,
        "Geometry": {
            "BoundingBox": {
                "Width": 0.03180000185966492,
                "Height": 0.07208999991416931,
                "Left": 0.23874999582767487,
                "Top": 0.2536500096321106
            }
        }
    }, {
        "Name": "norwich_city",
        "Confidence": 66.148,
        "Geometry": {
            "BoundingBox": {
                "Width": 0.03180000185966492,
                "Height": 0.07208999991416931,
                "Left": 0.23874999582767487,
                "Top": 0.2536500096321106
            }
        }
    }]


@pytest.mark.parametrize(
    'program_info, expected_team_ids', [
        ({'Team_Info': 'AVL V NOR'}, [
            {'id': 'aston_villa', 'name': 'Aston Villa'},
            {'id': 'norwich_city', 'name': 'Norwich City'}
        ]),
        ({'Team_Info': 'BOU V ARS'}, [
            {'id': 'arsenal', 'name': 'Arsenal'},
            {'id': 'bournemouth', 'name': 'AFC Bournemouth'}
        ]),
        ({'Team_Info': 'MUN V EVE'}, [
            {'id': 'everton', 'name': 'Everton'},
            {'id': 'manchester_united', 'name': 'Manchester United'}
        ]),
    ])  # yapf: disable
def test_team_logo_check_execute_yields_expected_logo(program_info, expected_team_ids, detected_logos):
    sut = TeamLogoCheck()

    res = dict(sut.execute(program_info, detected_logos))

    assert expected_team_ids[0] == res['Team1_Logo_Expected']
    assert expected_team_ids[1] == res['Team2_Logo_Expected']


@pytest.mark.parametrize(
    'program_info, team_1_detections, team_2_detections', [
        ({'Team_Info': 'AVL V NOR'}, ('aston_villa', 1), ('norwich_city', 2)),
    ])  # yapf: disable
def test_team_logo_check_execute_yields_detections(program_info, team_1_detections, team_2_detections, detected_logos):
    sut = TeamLogoCheck()

    res = dict(sut.execute(program_info, detected_logos))

    team_1_id, team_1_detection_count = team_1_detections
    team_2_id, team_2_detection_count = team_2_detections

    assert team_1_id == res['Team1_Logo_Detected'][0]["id"]
    assert team_1_detection_count == len(res['Team1_Logo_Detected'])

    assert team_2_id == res['Team2_Logo_Detected'][0]["id"]
    assert team_2_detection_count == len(res['Team2_Logo_Detected'])


@pytest.mark.parametrize(
    'program_info, expected_confidence', [
        ({'Team_Info': 'AVL V NOR'}, [88.08, 78.08]),
        ({'Team_Info': 'NOR V ARS'}, [88.08, 78.08]),
        ({'Team_Info': 'MUN V EVE'}, [88.08, 78.08]),
    ])  # yapf: disable
def test_team_logo_check_execute_yields_expected_confidence(program_info, expected_confidence, detected_logos):
    sut = TeamLogoCheck()

    res = dict(sut.execute(program_info, detected_logos))

    assert expected_confidence[0] == pytest.approx(res['Team1_Logo_Confidence'], 0.01)
    assert expected_confidence[1] == pytest.approx(res['Team2_Logo_Confidence'], 0.01)


@pytest.mark.parametrize(
    'program_info, expeted_team_logos_match', [
        ({'Team_Info': 'AVL V NOR'}, [True, True]),
        ({'Team_Info': 'NOR V AVL'}, [True, True]),
        ({'Team_Info': 'AVL V MCI'}, [True, False]),
        ({'Team_Info': 'MCI V AVL'}, [True, False]),
        ({'Team_Info': 'ARS V NOR'}, [False, True]),
        ({'Team_Info': 'NOR V ARS'}, [False, True]),
        ({'Team_Info': 'EVE V MCI'}, [False, False]),
    ])  # yapf: disable
def test_team_logo_check_execute_yields_team_logos_match(program_info, expeted_team_logos_match, detected_logos):
    sut = TeamLogoCheck()

    res = dict(sut.execute(program_info, detected_logos))

    assert expeted_team_logos_match[0] == res['Team1_Logo_Status']
    assert expeted_team_logos_match[1] == res['Team2_Logo_Status']
