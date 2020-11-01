import builtins
import logging
import boto3
import botocore
import threading

from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from dateutil import tz
from sentry_sdk import capture_exception
from threading import Thread
from time import sleep

# from .aws.ddb import get_item, put_item, update_item
from .datetime import make_timestamp
from .metrics import post_count_metric

from . import threads


log = logging.getLogger(APP_NAME)


TABLE_NAME = 'app_leader'
LEADERSHIP_GRACE_PERIOD_SECS = 60


class Leader(Thread):

    def __init__(self, app_name=APP_NAME, device_name=DEVICE_NAME):
        super(Leader, self).__init__()
        self.daemon = True

        self._ddb = boto3.resource('dynamodb')
        self._ddb_table = self._ddb.Table(TABLE_NAME)

        self._app_name = app_name
        self._device_name = device_name

    def yield_to_leader(self):
        log.info('Attempting leadership of {} as {}...'.format(self._app_name, self._device_name))
        while True:
            put_conflict = False
            timestamp = make_timestamp()
            unix_timestamp = int((timestamp.replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds())
            try:
                response = self._ddb_table.put_item(
                    Item={
                        'app_name': self._app_name,
                        'timestamp': unix_timestamp,
                        'device_name': self._device_name,
                    },
                    ConditionExpression=Attr("app_name").not_exists(),
                    # ensure that the permitted leader is known
                    ReturnValues='ALL_NEW'
                )
                log.info('DEBUG: DDB response is {}'.format(vars(response)))
                log.info('Acquired leadership of {} as {}.'.format(self._app_name, self._device_name))
                # break
            except botocore.exceptions.ClientError as e:
                # Ignore the ConditionalCheckFailedException, bubble up
                # other exceptions.
                if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise
                log.info('DEBUG: put failed {}'.format(str(e)))
                put_conflict = True

            #FIXME: remove
            put_conflict = True
            if put_conflict:
                try:
                    response = self._ddb_table.update_item(
                        Item={
                            'app_name': self._app_name,
                            'timestamp': unix_timestamp,
                            'device_name': self._device_name,
                        },
                        ConditionExpression=Attr("timestamp").lt(unix_timestamp - LEADERSHIP_GRACE_PERIOD_SECS),
                        # ensure that the permitted leader is known
                        ReturnValues='ALL_NEW'
                    )
                    log.info('DEBUG: DDB response is {}'.format(vars(response)))
                    #log.info('Acquired leadership of {} as {}.'.format(self._app_name, self._device_name))
                    # break
                except botocore.exceptions.ClientError as e:
                    # Ignore the ConditionalCheckFailedException, bubble up
                    # other exceptions.
                    if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                        raise
                    log.info('DEBUG: {}'.format(str(e)))
                    put_failed = True

            # TODO: remove
            sleep(5)
            break
            # never spin
            # threads.interruptable_sleep.wait(10)

    # noinspection PyBroadException
    def run(self):
        while True:
            try:
                sleep(60)
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue
