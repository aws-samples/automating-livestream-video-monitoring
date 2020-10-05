import os
from datetime import datetime
from pathlib import Path

from decimal import Decimal

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from common.utils import (DDBUpdateBuilder, check_enabled, cleanup_dir,
                          convert_csv_to_ddb, convert_str_to_bool, dynamodb,
                          parse_date_time_from_str, parse_date_time_to_str, convert_to_ddb,
                          query_item_ddb)
test_table_name = 'test'
TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


@pytest.fixture()
def local_ddb(request):
    local_ddb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    print('setting up table in local ddb')
    local_ddb.create_table(
        TableName=test_table_name,
        KeySchema=[
            {
                'AttributeName': 'Test_Hashkey',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'Test_RangeKey',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'Test_Hashkey',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'Test_RangeKey',
                'AttributeType': 'N'
            },

        ],
        BillingMode='PAY_PER_REQUEST'
    )

    yield local_ddb
    local_ddb.Table(test_table_name).delete()


def test_convert_csv_to_ddb(local_ddb):
    test_csv = os.path.join(TEST_DATA_DIR, 'test-csv-import.csv')
    hash_key = 'test_str'
    convert_csv_to_ddb(test_csv, test_table_name, ddb_client=local_ddb)
    # verify the table is successfully updated.

    ddb_table = local_ddb.Table(test_table_name)
    response = ddb_table.query(KeyConditionExpression=Key('Test_Hashkey').eq(hash_key))
    ddb_items = response['Items']
    assert len(ddb_items) == 4
    print(ddb_items)

    assert ddb_items[0]['Test_RangeKey'] == 1
    assert ddb_items[1]['Test_RangeKey'] == 3
    assert float(ddb_items[1]['Test_Num_Column']) == 2.2222
    assert ddb_items[2]['Test_RangeKey'] == 5
    assert ddb_items[3]['Test_RangeKey'] == 9
    assert ddb_items[3]['Test_Str_Column'] == 'test'


def test_query_item_pagination(local_ddb):
    hash_key = 'test_hash'
    # set up the table with 200 elements
    ddb_table = local_ddb.Table(test_table_name)
    for i in range(200):
        ddb_table.put_item(Item={'Test_Hashkey': hash_key, 'Test_RangeKey': i})

    # make sure the query results contain all of them
    results = query_item_ddb(test_table_name, ddb_client=local_ddb,
                             KeyConditionExpression=Key('Test_Hashkey').eq(hash_key), Limit=50)
    assert len(results) == 200

    results = query_item_ddb(test_table_name, ddb_client=local_ddb,
                             KeyConditionExpression=Key('Test_Hashkey').eq('non_existent'), Limit=50)
    assert len(results) == 0


@pytest.fixture
def ddb_test_table_stub():
    test_table = dynamodb.Table('test-table')
    with Stubber(test_table.meta.client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def test_ddb_update_builder_context_manager(ddb_test_table_stub):
    ddb_test_table_stub.add_response('update_item', {})

    # asserts that ddb.Table.updates is called upon exiting the context
    # manager via a call to DDBUpdateBuilder.
    with DDBUpdateBuilder(key={'Key': 'test-key'}, table_name='test-table') as update_builder:
        update_builder.update_attr('test', 'some-value')


def test_parse_date_time():
    datetime_str = '2020-01-21T16:59:07.001000Z'
    parsed_date_time = parse_date_time_from_str(datetime_str)
    assert datetime(year=2020, month=1, day=21, hour=16, minute=59, second=7, microsecond=1000) == parsed_date_time
    assert datetime_str == parse_date_time_to_str(parsed_date_time)


@check_enabled('some_check_enabled')
def fake_handler(event, context):
    return True


@pytest.mark.parametrize('event, expected_result', [
    ({'config': {'some_check_enabled': True}}, True),
    (None, None),  # missing config
    ({}, None)  # missing config
])  # yapf: disable
def test_check_enabled_decorator(event, expected_result):
    res = fake_handler(event, '')
    assert expected_result == res


BASE_DIR = '/tmp/test_dir_cleanup/'


@cleanup_dir(BASE_DIR)
def fake_dir_cleanup_handler(event, context):
    assert len(os.listdir(BASE_DIR)) == 0


def test_dir_cleanup_handler():
    # set up test with directories and files
    Path(BASE_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(BASE_DIR, 'nested')).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(BASE_DIR, 'test-0.txt')).touch()
    Path(os.path.join(BASE_DIR, 'test-1.txt')).touch()
    Path(os.path.join(BASE_DIR, 'nested/test-2.txt')).touch()
    os.symlink(os.path.join(BASE_DIR, 'nested/test-2.txt'), os.path.join(BASE_DIR, 'smlink.txt'))
    os.link(os.path.join(BASE_DIR, 'nested/test-2.txt'), os.path.join(BASE_DIR, 'hardlink.txt'))
    assert len(os.listdir(BASE_DIR)) == 5

    fake_dir_cleanup_handler({}, {})
    assert len(os.listdir(BASE_DIR)) == 0

    # set up test with empty directory
    Path(BASE_DIR).mkdir(parents=True, exist_ok=True)
    fake_dir_cleanup_handler({}, {})
    assert len(os.listdir(BASE_DIR)) == 0


def test_str_to_bool():
    assert convert_str_to_bool('True')
    assert convert_str_to_bool('TRUE')
    assert convert_str_to_bool('true')
    assert not convert_str_to_bool('')
    assert not convert_str_to_bool('False')
    assert not convert_str_to_bool('FALSE')
    assert not convert_str_to_bool('false')
    assert not convert_str_to_bool('1')
    assert not convert_str_to_bool('0')


@pytest.mark.parametrize(
    'in_val, expected', [
        ('some string', 'some string'),
        (10, 10),
        ([9.8, 3.14159, 1.618], [Decimal('9.8'), Decimal('3.14159'), Decimal('1.618')]),
        ({
            'a': 'something',
            'b': 0.0304,
            'c': {
                'c1': 'inner',
                'c2': 0.3333,
                'c3': 12345.
            }
        }, {
            'a': 'something',
            'b': Decimal('0.0304'),
            'c': {
                'c1': 'inner',
                'c2': Decimal('0.3333'),
                'c3': Decimal('12345.0')
            }
        })
    ]  # yapf: disable
)
def test_process_detections(in_val, expected):
    res = convert_to_ddb(in_val)

    assert expected == res
