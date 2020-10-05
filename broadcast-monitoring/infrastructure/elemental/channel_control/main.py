import json
import boto3
import logging
import os

medialive = boto3.client('medialive')
logging.basicConfig()
logger = logging.getLogger('ChannelControl')
logger.setLevel(logging.INFO)

CHANNEL_ID = os.getenv('CHANNEL_ID')


def start_channel_handler(event, context):
    logger.info('Received event: %s', json.dumps(event, indent=2))
    medialive.start_channel(
        ChannelId=CHANNEL_ID
    )
    logger.info('successfully started channel')


def stop_channel_handler(event, context):
    logger.info('Received event: %s', json.dumps(event, indent=2))
    medialive.stop_channel(
        ChannelId=CHANNEL_ID
    )
    logger.info('successfully stopped channel')
