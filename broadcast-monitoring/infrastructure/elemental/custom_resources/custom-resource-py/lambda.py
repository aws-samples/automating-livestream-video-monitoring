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
#  permissions and limitations under the License.
# @author Solution Builders - modified by AWS SA R&D team
# @function CFN Custom Resource
# @description cloudformation custom resource to create MediaLive and
# MediaPackage resources
#
##############################################################################
import json
import uuid
from crhelper import CfnResource
import libs.mediapackage as MediaPackage
import libs.medialive as MediaLive



# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL', sleep_on_delete=120, ssl_verify=None)


def get_event_details(event):
    request = event['RequestType']
    resource = event['ResourceProperties']['Resource']
    return request, resource

@helper.create
def create(event,context):
    print('Received event: ', json.dumps(event, indent=2))
    request, resource = get_event_details(event)
    config = event['ResourceProperties']
    responseData = {}
    print('REQUEST::{}::{}'.format(request, resource))
    print('CONFIG::{}'.format(config))

    if resource == 'MediaLiveInput':

        if 'MP4_FILE' in config['Type']:
            responseData = MediaLive.create_file_input(config)
        else:
            responseData = MediaLive.create_pull_input(config)
        id = responseData['Id']

    elif resource == 'MediaLiveChannel':
        responseData = MediaLive.create_channel(config)
        id = responseData['ChannelId']

    elif resource == 'MediaPackageChannel':
        responseData = MediaPackage.create_channel(config)
        id = responseData['ChannelId']

    elif resource == 'MediaPackageEndPoint':
        responseData = MediaPackage.create_endpoint(config)
        id = responseData['Id']

    elif resource == 'UUID':
        responseData = {'UUID': str(uuid.uuid4())}
        id = responseData['UUID']

    else:
        msg = 'Create failed, {} not defined in the Custom Resource'.format(resource)
        print(msg)
        raise ValueError(msg)

    helper.Data.update(responseData)
    return id


@helper.update
def update(event, context):
    request, resource = get_event_details(event)

    if resource == 'MediaPackageEndPoint':
        responseData = MediaPackage.update_endpoint(event['PhysicalResourceId'])
        helper.Data.update(responseData)
        return responseData['Id']
    else:
        print('RESPONSE:: {} Not supported. no op'.format(request))


@helper.delete
def delete(event, context):
    request, resource = get_event_details(event)
    if event['PhysicalResourceId'] != 'FailedCreation':
        if resource == 'MediaLiveChannel':
            MediaLive.delete_channel(event['PhysicalResourceId'])

        elif resource == 'MediaPackageChannel':
            MediaPackage.delete_channel(event['PhysicalResourceId'])

        else:
            # mediapackage endpoints are deleted as part of
            # the the channel deletes so not included here, sending default success response
            print('RESPONSE:: {} : delete not required, sending success response'.format(resource))
    else:
        print('RESPONSE:: {} : delete not required, sending success response'.format(resource))



def handler(event, context):
    helper(event, context)
