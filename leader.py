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
from .datetime import make_timestamp, make_unix_timestamp
from .aws.metrics import post_count_metric

from . import threads


log = logging.getLogger(APP_NAME)


TABLE_NAME = 'app_leader'
ELECTION_RETRY_INTERVAL_SECS = 10
ELECTION_UPDATE_INTERVAL_SECS = 20
LEADERSHIP_GRACE_PERIOD_SECS = 300


class Leader(Thread):

    def __init__(self, app_name=APP_NAME, device_name=DEVICE_NAME):
        super(Leader, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._ddb = boto3.resource('dynamodb')
        self._ddb_table = self._ddb.Table(TABLE_NAME)

        self._app_name = app_name
        self._device_name = device_name

    def _get_leader(self):
        response_item = None
        try:
            response = self._ddb_table.get_item(
                Key={
                    'app_name': self._app_name
                }
            )
            response_item = response['Item']
        except (ClientError, KeyError):
            pass
        return response_item

    def _log_leader(self):
        response = self._get_leader()
        if response is not None:
            log.info('Elected leader is currently {} at {}.'.format(
                response['device_name'],
                make_timestamp(int(response['unix_timestamp']))))

    def _handle_election_failure(self):
        if datetime.now().minute % 5 == 0:
            self._log_leader()
        threads.interruptable_sleep.wait(ELECTION_RETRY_INTERVAL_SECS)

    def _update_leadership(self, unix_timestamp):
        success = False
        try:
            self._ddb_table.update_item(
                Key={
                    'app_name': self._app_name
                },
                UpdateExpression='SET device_name = :d, unix_timestamp = :t',
                ExpressionAttributeValues={
                    ':d': self._device_name,
                    ':t': unix_timestamp
                },
                ConditionExpression=Attr("device_name").eq(self._device_name) | Attr("unix_timestamp").lt(unix_timestamp - LEADERSHIP_GRACE_PERIOD_SECS),
                ReturnValues='UPDATED_NEW'
            )
            success = True
        except ClientError as e:
            # Ignore the ConditionalCheckFailedException, bubble up
            # other exceptions.
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
        return success

    def surrender_leadership(self):
        try:
            self._ddb_table.delete_item(
                Key={
                    'app_name': self._app_name
                },
                ConditionExpression="device_name IN (:d)",
                ExpressionAttributeValues={
                    ":d": self._device_name
                }
            )
            log.info('Surrendered leadership of {} as {}.'.format(self._app_name, self._device_name))
        except ClientError as e:
            if e.response['Error']['Code'] != "ConditionalCheckFailedException":
                raise

    def yield_to_leader(self):
        self._log_leader()
        log.info('Attempting leadership of {} as {}...'.format(self._app_name, self._device_name))
        while True:
            unix_timestamp = make_unix_timestamp()
            try:
                self._ddb_table.put_item(
                    Item={
                        'app_name': self._app_name,
                        'unix_timestamp': unix_timestamp,
                        'device_name': self._device_name,
                    },
                    ConditionExpression=Attr("app_name").not_exists()
                )
            except ClientError as e:
                # Ignore the ConditionalCheckFailedException, bubble up
                # other exceptions.
                if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise
                if not self._update_leadership(unix_timestamp):
                    self._handle_election_failure()
                    continue
            # success
            log.info('Acquired leadership of {} as {}.'.format(self._app_name, self._device_name))
            break

    def run(self):
        log.info('Maintaining leadership of {} as {}'.format(self._app_name, self._device_name))
        while True:
            try:
                if threads.shutting_down:
                    log.warn('No longer re-electing leadership due to shutdown.')
                    break
                if not self._update_leadership(make_unix_timestamp()):
                    # we've lost leadership
                    log.warning('Failure to refresh leadership of {} by {}.'.format(
                        self._app_name,
                        self._device_name))
                    # FIXME: terminate application
                    break
                threads.interruptable_sleep.wait(ELECTION_UPDATE_INTERVAL_SECS)
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue
