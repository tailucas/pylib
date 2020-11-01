import builtins
import logging
import boto3
import botocore
import threading

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from dateutil import tz
from sentry_sdk import capture_exception
from threading import Thread
from time import sleep

# from .aws.ddb import get_item, put_item, update_item
from .datetime import make_timestamp
from .aws.metrics import post_count_metric

from . import threads


log = logging.getLogger(APP_NAME)


TABLE_NAME = 'app_leader'
ELECTION_RETRY_INTERVAL_SECS = 10
LEADERSHIP_GRACE_PERIOD_SECS = 60


class Leader(Thread):

    def __init__(self, app_name=APP_NAME, device_name=DEVICE_NAME):
        super(Leader, self).__init__()
        self.daemon = True

        self._ddb = boto3.resource('dynamodb')
        self._ddb_table = self._ddb.Table(TABLE_NAME)

        self._app_name = app_name
        self._device_name = device_name

    def _handle_election_failure(self):
        if datetime.now().minute % 5 == 0:
            try:
                response = self._ddb_table.get_item(
                    Key={
                        'app_name': self._app_name,
                    }
                )
                log.info('Elected leader is currently {}.'.format(response['Item']['device_name']))
            except (ClientError, KeyError):
                pass
        # try to re-aquire leadership
        threads.interruptable_sleep.wait(ELECTION_RETRY_INTERVAL_SECS)

    def yield_to_leader(self):
        log.info('Attempting leadership of {} as {}...'.format(self._app_name, self._device_name))
        while True:
            timestamp = make_timestamp()
            unix_timestamp = int((timestamp.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds())
            try:
                self._ddb_table.put_item(
                    Item={
                        'app_name': self._app_name,
                        'unix_timestamp': unix_timestamp,
                        'device_name': self._device_name,
                    },
                    ConditionExpression=Attr("app_name").not_exists() & Attr("device_name").not_exists()
                )
            except ClientError as e:
                # Ignore the ConditionalCheckFailedException, bubble up
                # other exceptions.
                if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise
                self._handle_election_failure()
                continue
            try:
                self._ddb_table.update_item(
                    Key={
                        'app_name': self._app_name,
                        'device_name': self._device_name
                    },
                    UpdateExpression='SET unix_timestamp = :t',
                    ExpressionAttributeValues={
                        ':t': unix_timestamp
                    },
                    ConditionExpression=Attr("unix_timestamp").lt(unix_timestamp - LEADERSHIP_GRACE_PERIOD_SECS),
                    ReturnValues='UPDATED_NEW'
                )
            except ClientError as e:
                # Ignore the ConditionalCheckFailedException, bubble up
                # other exceptions.
                if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise
                self._handle_election_failure()
                continue
            # success
            log.info('Acquired leadership of {} as {}.'.format(self._app_name, self._device_name))
            break

    # noinspection PyBroadException
    def run(self):
        while True:
            try:
                if threads.shutting_down:
                    break
                threads.interruptable_sleep.wait(ELECTION_RETRY_INTERVAL_SECS)
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue
