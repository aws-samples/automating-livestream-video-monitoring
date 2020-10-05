# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import argparse
import boto3
from common.utils import convert_csv_to_ddb
import logging

logging.basicConfig()

# command line arguments
parser = argparse.ArgumentParser(
    description='Write CSV records to DynamoDB table. CSV Header must map to dynamo table field names.')
parser.add_argument('csvFile', help='Path to csv file location')
parser.add_argument('table', help='Dynamo db table name')
parser.add_argument('delimiter', default=',', nargs='?', help='Delimiter for csv records (default=,)')
parser.add_argument('region', default='us-east-1', nargs='?', help='Dynamo db region name (default=us-east-1')
parser.add_argument('endpoint', default='', nargs='?', help='endpoint for DDB. default empty')

if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    # dynamodb and table initialization
    if args.endpoint:
        dynamodb = boto3.resource('dynamodb', region_name=args.region, endpoint_url=args.endpoint)
    else:
        dynamodb = boto3.resource('dynamodb', region_name=args.region)
    # write records to dynamo db
    convert_csv_to_ddb(args.csvFile, args.table, args.delimiter)
