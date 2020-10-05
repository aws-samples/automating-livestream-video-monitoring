# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import csv
import json
import logging
import os
import re
import time
import shutil
from datetime import datetime
from decimal import Decimal
from functools import wraps

import boto3
from botocore.exceptions import ClientError, ParamValidationError

from .config import LOG_LEVEL, UTC_TIME_FMT, WORKING_DIR

logger = logging.getLogger('Utils')
logger.setLevel(LOG_LEVEL)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')
secretsmanager = boto3.client('secretsmanager')


class ThrottlingException(Exception):
    pass


def get_s3_object_latest_version_id(s3_bucket, s3_key):
    s3_resource = boto3.resource('s3')
    s3_object = s3_resource.Object(s3_bucket, s3_key)
    return s3_object.version_id


def read_file_from_s3_w_versionid(s3_bucket, s3_key, versionid):
    try:
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key, VersionId=versionid)
        logger.info(f'Buffered s3://{s3_bucket}/{s3_key}?VersionId={versionid}')
        s3object = response['Body'].read().decode('utf-8')
    except ClientError as e:
        logger.error(f'Error downloading from s3://{s3_bucket}/{s3_key}?VersionId={versionid}', exc_info=True)
        raise e
    return s3object


def from_s3_object(s3_bucket, s3_key, buf):
    timer = Timer(f'download s3://{s3_bucket}/{s3_key} to memory', logger_fn=logger.info)
    try:
        timer.tic()
        s3.download_fileobj(s3_bucket, s3_key, buf)
        timer.toc()
    except ClientError as e:
        logger.error(f'Error downloading from s3://{s3_bucket}/{s3_key}', exc_info=True)
        raise e
    else:
        buf.seek(0)
        return buf


def download_file_from_s3(s3_bucket, s3_key, dest_file=None):
    if dest_file is None:
        dest_file = WORKING_DIR + os.path.basename(s3_key)
    timer = Timer(f'download s3://{s3_bucket}/{s3_key} to {dest_file}', logger_fn=logger.info)
    try:
        timer.tic()
        s3.download_file(s3_bucket, s3_key, dest_file)
        timer.toc()
    except ClientError as e:
        logger.error(f'Error downloading from s3://{s3_bucket}/{s3_key}', exc_info=True)
        raise e
    return dest_file


def upload_to_s3(s3_bucket, s3_key, body_bytes, **kwargs):
    timer = Timer(f'upload {len(body_bytes)} bytes to s3://{s3_bucket}/{s3_key}', logger_fn=logger.info)
    try:
        timer.tic()
        s3.put_object(ACL='bucket-owner-full-control', Bucket=s3_bucket, Key=s3_key, Body=body_bytes, **kwargs)
        timer.toc()
    except ClientError as e:
        logger.error(f'Error uploading to s3://{s3_bucket}/{s3_key}', exc_info=True)
        raise e


def upload_file_to_s3(s3_bucket, s3_key, filename, **kwargs):
    timer = Timer(f'upload {filename} bytes to s3://{s3_bucket}/{s3_key}', logger_fn=logger.info)
    try:
        timer.tic()
        s3.upload_file(Filename=filename, Bucket=s3_bucket, Key=s3_key, **kwargs)
        timer.toc()
    except ClientError as e:
        logger.error(f'Error uploading {filename} to s3://{s3_bucket}/{s3_key}', exc_info=True)
        raise e


def put_item_ddb(table_name, item, ddb_client=None):
    if ddb_client is not None:
        table = ddb_client.Table(table_name)
        logger.info('putting in ddb using ddb client override')
    else:
        table = dynamodb.Table(table_name)
    try:
        table.put_item(Item=item)
        logger.info(f'success putting item to {table_name} DDB table.')
    except ClientError as e:
        logger.error(f'Error putting item to ddb: {table_name}', exc_info=True)
        raise e


def update_item_ddb(table_name, ddb_client=None, **kwargs):
    if ddb_client is not None:
        table = ddb_client.Table(table_name)
        logger.info('updating ddb using ddb client override')
    else:
        table = dynamodb.Table(table_name)
    try:
        table.update_item(**kwargs)
        logger.info(f'Success updating item to {table_name} DDB table.')
    except ClientError as e:
        logger.error(f'Error updating item to ddb: {table_name}', exc_info=True)
        raise e


def query_item_ddb(table_name, ddb_client=None, **kwargs):
    if ddb_client is not None:
        table = ddb_client.Table(table_name)
        logger.info('querying ddb using ddb client override')
    else:
        table = dynamodb.Table(table_name)
    try:
        response = table.query(**kwargs)
        for i, item in enumerate(response["Items"]):
            logger.debug(f'item {i}: {json.dumps(item, cls=DecimalEncoder)}')
        result = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.query(ExclusiveStartKey=response['LastEvaluatedKey'], **kwargs)
            logger.info(f'DDBQuery: Found {len(response["Items"])} items in next page.')
            result.extend(response['Items'])
        return result
    except ClientError as e:
        logger.error(f'Error querying {table_name} DDB table', exc_info=True)
        raise e


def get_item_ddb(table_name, ddb_client=None, **kwargs):
    if ddb_client is not None:
        table = ddb_client.Table(table_name)
        logger.info('getting ddb data using ddb client override')
    else:
        table = dynamodb.Table(table_name)

    try:
        valid_args = ['Key', 'AttributesToGet', 'ProjectionExpression']
        response = table.get_item(**{k: v for k, v in kwargs.items() if k in valid_args})
        item = response['Item']
    except ClientError as e:
        logger.error('Error querying %s DDB table', table_name, exc_info=True)
        raise e
    else:
        logger.info('Success querying %s DDB table. Found item', table_name)
        logger.debug('item %s', json.dumps(item, cls=DecimalEncoder))
        return item


def convert_csv_to_ddb(csv_file_path, table_name, delimiter=',', ddb_client=None):
    if ddb_client is not None:
        table = ddb_client.Table(table_name)
    else:
        table = dynamodb.Table(table_name)

    # each entry in header row should be in the format of "<ColumnName> (Type)"
    # e.g. "Stream_ID (S)" or "Duration_Sec (N)"
    pattern = re.compile(r'([a-zA-Z0-9_\s]+) \(([A-Z]+)\)')

    def _parse_column_schema(col_header, pattern):
        m = re.search(pattern, col_header)
        return m.group(1), m.group(2)

    def _get_csv_data(file, csv_delimiter):
        dr = csv.DictReader(file, delimiter=csv_delimiter)
        for d in dr:
            row_data = {}
            for field_name in dr.fieldnames:
                ddb_column_name, ddb_column_type = _parse_column_schema(field_name, pattern)
                if d[field_name]:
                    if ddb_column_type == 'N':
                        row_data[ddb_column_name] = float(d[field_name])
                    elif ddb_column_type == 'BOOL':
                        row_data[ddb_column_name] = bool(d[field_name])
                    else:
                        row_data[ddb_column_name] = d[field_name]
            yield row_data

    with open(csv_file_path) as csv_file:
        for data in _get_csv_data(csv_file, delimiter):
            item = convert_dict_float_to_dec(data)
            logger.info(f'going to put {item} to DDB table: {table.name}')
            table.put_item(Item=item)


class DDBUpdateBuilder(object):
    def __init__(self, key, table_name, ddb_client=None):
        self.key = key
        self.table_name = table_name
        self.ddb_client = ddb_client
        self.update_expressions = []
        self.expression_attr_names = {}
        self.expression_attr_vals = {}

    def update_attr(self, attr_name, attr_value, convert=lambda x: x):
        self.update_expressions.append(f'#{attr_name} = :{attr_name}')
        self.expression_attr_names[f'#{attr_name}'] = attr_name
        self.expression_attr_vals[f':{attr_name}'] = convert(attr_value)

    def update_params(self):
        return {
            'Key': self.key,
            'UpdateExpression': 'set ' + ','.join(self.update_expressions),
            'ExpressionAttributeNames': self.expression_attr_names,
            'ExpressionAttributeValues': self.expression_attr_vals
        }

    def commit(self):
        if self.update_expressions:
            ddb_update_item = self.update_params()
            update_item_ddb(self.table_name, self.ddb_client, **ddb_update_item)
        else:
            logger.info('DDBUpdateBuilder: nothing to update. will do nothing.')

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        logger.info(f'Committing params to dynamodb [{self.table_name}: {self.key}]')
        self.commit()


def detect_text_from_image(s3_bucket, s3_key):
    try:
        response = rekognition.detect_text(
            Image={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            }
        )
        return response['TextDetections']
    except ClientError as e:
        logger.error(f'Error calling Rekognition TextDetection for s3://{s3_bucket}/{s3_key}', exc_info=True)
        error_code = e.response['Error']['Code']
        logger.error(f'Rekognition error code: {error_code}')
        if error_code == 'ThrottlingException':
            raise ThrottlingException(e)
        else:
            raise e


def parse_date_time_from_str(date_time_str):
    return datetime.strptime(date_time_str, UTC_TIME_FMT)


def parse_date_time_to_str(date_time):
    return datetime.strftime(date_time, UTC_TIME_FMT)


def convert_float_to_dec(num):
    """
    Convert a float number to decimal. This is required when writing floating point numbers to DDB.
    :param num: a float
    :return: representation of the number in Decimal
    """
    return Decimal(str(num))


def convert_dict_float_to_dec(dict):
    """
    Given a dict, take any values that is a float number and convert it to decimal so it can be written to DDB.
    :param dict:
    :return: a new dict object with all floating number values replaced with Decimal representation.
    """
    new_dict = {}
    for key in dict:
        if isinstance(dict[key], float):
            new_dict[key] = convert_float_to_dec(dict[key])
        else:
            new_dict[key] = dict[key]
    return new_dict


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


class Timer(object):
    def __init__(self, text, logger_fn=print):
        self.text = text
        self._start_time = None
        self.logger_fn = logger_fn

    def tic(self):
        self._start_time = time.perf_counter()

    def toc(self):
        duration = time.perf_counter() - self._start_time
        self._start_time = None
        if self.logger_fn is not None:
            self.logger_fn('{} took  {:0.4f} seconds'.format(self.text, duration))


class CheckDisabledError(Exception):
    pass


def check_enabled(check_name):
    """
    Validates that a check is enabled and only executes a handler or function when, check evaluates true

    :param check_name: Name of the stream processing check to parse the config for
    :return: decorator function to be applied to a handler
    """
    if check_name is None:
        raise ValueError('argument must be a valid string')

    def inner(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                event = kwargs.get('event', args[0])
                config = event.get('config')
                logger.info('Processing [%s] with config: %s', check_name, config)
                if not config[check_name]:
                    raise CheckDisabledError(f'{check_name} check disabled')
            except Exception as e:
                # Handle exceptions when checking
                res = None
                logger.error(e)
            else:
                # Execute the wrapped handler when no exception occurs
                logger.info('[%s] check enabled. Executing handler', check_name)
                res = f(*args, **kwargs)

            return res

        wrapper.config_name = check_name
        return wrapper

    return inner


def cleanup_dir(dir_path=WORKING_DIR):
    """
    A function decorator that cleans up file directory before executing.
    """

    def rm_content(dir_path):
        rm_count = 0
        for filename in os.listdir(dir_path):
            filepath = os.path.join(dir_path, filename)
            if os.path.isfile(filepath) or os.path.islink(filepath):
                os.remove(filepath)
            else:
                shutil.rmtree(filepath)
            rm_count += 1
        logger.info(f'removed {rm_count} file/directories from {dir_path}')

    def inner(f):
        @wraps(f)
        def dir_cleanup_wrapper(*args, **kwargs):
            rm_content(dir_path)
            result = f(*args, **kwargs)
            return result

        return dir_cleanup_wrapper

    return inner


def get_secret(secret_name):
    try:
        get_secret_value_response = secretsmanager.get_secret_value(SecretId=secret_name)
    except ParamValidationError as pe:  # noqa
        logger.error(f'Returning none for parameter validation error', exc_info=True)
        return None
    except ClientError as e:
        # raise_errors = [
        #     'DecryptionFailureException', 'InternalServiceErrorException', 'InvalidParameterException',
        #     'InvalidRequestException', 'ResourceNotFoundException'
        # ]
        logger.error(f'Error retrieving secret: {secret_name}', exc_info=True)
        raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = get_secret_value_response['SecretBinary']

        return secret


def convert_str_to_bool(string):
    return string.lower() == 'true'


def parse_expected_teams(team_info, expected_team_str):
    expected_team_abbr = expected_team_str.split(" V ")
    return [team_info.get_team_from_abbr(team_abbr) for team_abbr in expected_team_abbr]


def convert_to_ddb(node):
    if isinstance(node, float):
        return convert_float_to_dec(node)
    elif isinstance(node, dict):
        return {k: convert_to_ddb(v) for k, v in node.items()}
    elif type(node) is list:
        return [convert_to_ddb(el) for el in node]
    else:
        return node


def convert_from_ddb(data):
    if isinstance(data, dict):
        return {k: convert_from_ddb(v) for k, v in data.items()}
    elif type(data) is list:
        return [convert_from_ddb(el) for el in data]
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data
