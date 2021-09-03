#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Amazon Software License (the "License"). You may not   #
#  use this file except in compliance with the License. A copy of the        #
#  License is located at                                                     #
#                                                                            #
#      http://aws.amazon.com/asl/                                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################

from urllib.parse import urlparse
import boto3

mediapackage = boto3.client('mediapackage')
ssm = boto3.client('ssm')
responseData = {}


def create_channel(config):
    response = mediapackage.create_channel(
        Description='live-streaming-on-aws',
        Id=config['ChannelId']
    )
    responseData['ChannelId'] = config['ChannelId']
    responseData['PrimaryUrl'] = response['HlsIngest']['IngestEndpoints'][0]['Url']
    responseData['PrimaryUser'] = response['HlsIngest']['IngestEndpoints'][0]['Username']
    responseData['PrimaryPassParam'] = response['HlsIngest']['IngestEndpoints'][0]['Username']

    # Adding Primary U/P to SSM Parameter store
    ssm.put_parameter(
        Name=response['HlsIngest']['IngestEndpoints'][0]['Username'],
        Description='MediaPackage Primary Ingest Username',
        Value=response['HlsIngest']['IngestEndpoints'][0]['Password'],
        Type='String'
    )
    # FEATURE/P15424610
    # Dual ingest support added to MediaPackage, returning details for both Ingest
    # Endpoints. Update due for GA 08/28
    responseData['SecondaryUrl'] = response['HlsIngest']['IngestEndpoints'][1]['Url']
    responseData['SecondaryUser'] = response['HlsIngest']['IngestEndpoints'][1]['Username']
    responseData['SecondaryPassParam'] = response['HlsIngest']['IngestEndpoints'][1]['Username']
    # Adding Secondary U/P to SSM Parameter store
    ssm.put_parameter(
        Name=response['HlsIngest']['IngestEndpoints'][1]['Username'],
        Description='MediaPackage Secondary Ingest Username',
        Value=response['HlsIngest']['IngestEndpoints'][1]['Password'],
        Type='String'
    )
    print('RESPONSE::{}'.format(responseData))
    return responseData


def create_endpoint(config):
    if config.get('EndPoint') == 'HLS':
        response = mediapackage.create_origin_endpoint(
            ChannelId=config['ChannelId'],
            Id=config['ChannelId'] + '-hls',
            Description='Broadcast monitoring livestream',
            HlsPackage={
                'IncludeIframeOnlyStream': False,
                'PlaylistType': 'NONE',
                'PlaylistWindowSeconds': 60,
                'ProgramDateTimeIntervalSeconds': int(config['ProgramDateTimeIntervalSec']),
                'SegmentDurationSeconds': 6,
                'UseAudioRenditionGroup': False
            },
            ManifestName='index',
            StartoverWindowSeconds=int(config['StartoverWindow']),
            TimeDelaySeconds=0,
        )
    elif config.get('EndPoint') == 'DASH':
        response = mediapackage.create_origin_endpoint(
            ChannelId=config['ChannelId'],
            Id=config['ChannelId'] + '-dash',
            Description='Broadcast monitoring livestream',
            DashPackage={
                'ManifestWindowSeconds': 60,
                'MinBufferTimeSeconds': 30,
                'MinUpdatePeriodSeconds': 15,
                'Profile': 'NONE',
                'SegmentDurationSeconds': 2,
                'SuggestedPresentationDelaySeconds': 25
            },
            ManifestName='index',
            StartoverWindowSeconds=int(config['StartoverWindow']),
            TimeDelaySeconds=0,
        )
    elif config.get('EndPoint') == 'MSS':
        response = mediapackage.create_origin_endpoint(
            ChannelId=config['ChannelId'],
            Id=config['ChannelId'] + '-mss',
            Description='Broadcast monitoring livestream',
            MssPackage={
                'ManifestWindowSeconds': 60,
                'SegmentDurationSeconds': 2,
            },
            ManifestName='index',
            StartoverWindowSeconds=int(config['StartoverWindow']),
            TimeDelaySeconds=0,
        )
    else:
        print('RESPONSE:: EndPoint type [HLS,DASH,MSS] not defined')
        return

    parse_mediapackage_endpoint_info(response)
    print('RESPONSE::{}'.format(responseData))
    return responseData


def update_endpoint(endpoint_id):  # simply describe the endpoint
    response = mediapackage.describe_origin_endpoint(Id=endpoint_id)
    parse_mediapackage_endpoint_info(response)
    print('RESPONSE::{}'.format(responseData))
    return responseData


def parse_mediapackage_endpoint_info(response):
    url = urlparse(response['Url'])
    responseData['Id'] = response['Id']
    responseData['DomainName'] = url.hostname
    responseData['Path'] = '/' + url.path.split('/')[-3]
    responseData['Manifest'] = url.path[7:]


def delete_channel(ChannelId):
    response = mediapackage.list_origin_endpoints(
        ChannelId=ChannelId
    )
    for i in response['OriginEndpoints']:
        mediapackage.delete_origin_endpoint(
            Id=i['Id']
        )
    mediapackage.delete_channel(
        Id=ChannelId
    )
    print('RESPONSE:: Channel and EndPoints Deleted')
    return
