import pytest
import boto3
import os
from common.config import DDB_SCHEDULE_TABLE
from common.utils import convert_csv_to_ddb
from ..app.find_expected_program import find_expected_program_for_looping_input

table_name = DDB_SCHEDULE_TABLE
TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


@pytest.fixture()
def local_ddb(request):
    local_ddb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    print('setting up tables in local ddb')
    local_ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'Stream_ID',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'Start_Time',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'Stream_ID',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'Start_Time',
                'AttributeType': 'N'
            },

        ],
        BillingMode='PAY_PER_REQUEST'
    )

    test_data = os.path.join(TEST_DATA_DIR, 'test-schedule.csv')
    convert_csv_to_ddb(test_data, table_name, delimiter=',', ddb_client=local_ddb)
    print(f'loaded test data in local ddb table: {table_name}')
    yield local_ddb
    local_ddb.Table(table_name).delete()


def test_find_expected_program(local_ddb):
    # test data has 3 segments:
    # 1: 0-60
    # 2: 60-90
    # 3: 90-150
    stream_id = 'test_1'
    # first program
    program = find_expected_program_for_looping_input(stream_id, 0, 6, local_ddb)
    assert program['Start_Time'] == 0
    assert program['Event_ID'] == 'SIM-PROG1'

    # first program, straddle across to second program
    program = find_expected_program_for_looping_input(stream_id, 59, 6, local_ddb)
    assert program['Start_Time'] == 0
    assert program['Event_ID'] == 'SIM-PROG1'

    # second program
    program = find_expected_program_for_looping_input(stream_id, 60, 6, local_ddb)
    assert program['Start_Time'] == 60
    assert program['Event_ID'] == 'SIM-PROG2'

    # middle of second program
    program = find_expected_program_for_looping_input(stream_id, 80, 6, local_ddb)
    assert program['Start_Time'] == 60
    assert program['Event_ID'] == 'SIM-PROG2'

    # third program
    program = find_expected_program_for_looping_input(stream_id, 90, 6, local_ddb)
    assert program['Start_Time'] == 90
    assert program['Event_ID'] == 'SIM-PROG3'

    # segment start at the end of the last program. start back at 0
    program = find_expected_program_for_looping_input(stream_id, 150, 6, local_ddb)
    assert program['Start_Time'] == 0
    assert program['Event_ID'] == 'SIM-PROG1'

    # loop once
    program = find_expected_program_for_looping_input(stream_id, 220, 6, local_ddb)
    assert program['Start_Time'] == 60
    assert program['Event_ID'] == 'SIM-PROG2'

    # loop twice
    program = find_expected_program_for_looping_input(stream_id, 330, 6, local_ddb)
    assert program['Start_Time'] == 0
    assert program['Event_ID'] == 'SIM-PROG1'
