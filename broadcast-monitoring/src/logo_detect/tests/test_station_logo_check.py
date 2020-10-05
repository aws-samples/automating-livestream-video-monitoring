from pathlib import Path

import pytest
from ..app.station_logo_check import StationLogoCheck


@pytest.fixture
def station_test_data():
    return Path(__file__).parent.absolute().joinpath('data/stations.yaml')


@pytest.fixture
def station_test_check(station_test_data):
    return StationLogoCheck(file_name=station_test_data)


def test_station_check_ddb_attrs(station_test_data):
    sut = StationLogoCheck()
    assert sut.ddb_attrs == ['Detected_Station_Logos']


@pytest.mark.parametrize(
    'expected_program, data, expected', [
        (
            {'Station_Logo': 'BBC One'},
            [{'Name': 'bbc', 'Confidence': 71.1129}],
            [('Detected_Station_Logos', [{'Name': 'bbc', 'Confidence': 71.1129}]),
             ('Detected_Logo', 'BBC'),
             ('Detected_Logo_Confidence', 71.1129),
             ('Expected_Logo', 'BBC One'),
             ('Is_Expected_Logo', True)]
        ), (
            {'Station_Logo': 'Netflix'},
            [{'Name': 'hbo', 'Confidence': 88.888}, {'Name': 'netflix', 'Confidence': 77.777}],
            [('Detected_Station_Logos', [
                {'Name': 'hbo', 'Confidence': 88.888},
                {'Name': 'netflix', 'Confidence': 77.777}]),
             ('Detected_Logo', 'HBO'),
             ('Detected_Logo_Confidence', 88.888),
             ('Expected_Logo', 'Netflix'),
             ('Is_Expected_Logo', False)]
        ), (
            {'Station_Logo': 'HBO'},
            [],
            [('Detected_Station_Logos', []),
             ('Detected_Logo', None),
             ('Expected_Logo', 'HBO'),
             ('Is_Expected_Logo', False)]
        )
    ]
)  # yapf: disable
def test_station_check_execute(station_test_check, expected_program, data, expected):
    res = list(station_test_check.execute(expected_program, data))
    assert expected == res
