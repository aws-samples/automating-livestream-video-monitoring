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
import lib.cfnresponse as cfn
import lib.mediapackage as MediaPackage
import lib.medialive as MediaLive


def handler(event, context):
    # Each resource returns a promise with a json object to return cloudformation.
    try:
        print('Received event: %s', json.dumps(event, indent=2))
        request = event['RequestType']
        resource = event['ResourceProperties']['Resource']
        config = event['ResourceProperties']
        responseData = {}
        print('REQUEST::{}::{}'.format(request, resource))
        print('CONFIG::{}'.format(config))

        if request == 'Create':
            try:
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
                    print('Create failed, {} not defined in the Custom Resource'.format(resource))
                    cfn.send(event, context, 'FAILED', {}, context.log_stream_name)

                cfn.send(event, context, 'SUCCESS', responseData, id)
            except Exception as e:
                print('Exception: {}'.format(e))
                cfn.send(event, context, 'FAILED', {}, 'FailedCreation')
                print(e)

        elif request == 'Delete':
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

            cfn.send(event, context, 'SUCCESS', {})

        elif request == 'Update':
            if resource == 'MediaPackageEndPoint':
                responseData = MediaPackage.update_endpoint(event['PhysicalResourceId'])
                id = responseData['Id']
                cfn.send(event, context, 'SUCCESS', responseData, id)

            else:
                print('RESPONSE:: {} Not supported. no op'.format(request))
                cfn.send(event, context, 'SUCCESS', {})

    except Exception as e:
        print('Exception: {}'.format(e))
        cfn.send(event, context, 'FAILED', {}, context.log_stream_name)
        print(e)
