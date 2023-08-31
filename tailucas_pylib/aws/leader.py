import logging
import boto3


from botocore.exceptions import (
    ClientError,
    EndpointConnectionError
)


from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
from dateutil import tz
from sentry_sdk import capture_exception
from threading import Thread

from .datetime import make_timestamp, make_unix_timestamp

from . import threads


log = logging.getLogger(APP_NAME)  # type: ignore


TABLE_NAME = 'app_leader'
ELECTION_RETRY_INTERVAL_SECS = 10
ELECTION_UPDATE_INTERVAL_SECS = 20
LEADERSHIP_GRACE_PERIOD_SECS = 300


class Leader(Thread):

    def __init__(self, app_name=APP_NAME, device_name=DEVICE_NAME): # type: ignore
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
            device_name = response['device_name']
            timestamp = make_timestamp(int(response['unix_timestamp']))
            log.info(f'Elected leader is currently {device_name} at {timestamp}.')

    def _handle_election_failure(self):
        if datetime.now().minute % 5 == 0 and datetime.now().second < 10:
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
            log.info(f'Surrendered leadership of {self._app_name} as {self._device_name}.')
        except ClientError as e:
            if e.response['Error']['Code'] != "ConditionalCheckFailedException":
                raise

    def yield_to_leader(self):
        self._log_leader()
        log.info(f'Attempting leadership of {self._app_name} as {self._device_name}...')
        while not threads.shutting_down:
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
            log.info(f'Acquired leadership of {self._app_name} as {self._device_name}.')
            break

    def run(self):
        log.info(f'Maintaining leadership of {self._app_name} as {self._device_name}')
        while not threads.shutting_down:
            try:
                if not self._update_leadership(make_unix_timestamp()):
                    # we've lost leadership
                    log.warning(f'Failure to refresh leadership of {self._app_name} by {self._device_name}.')
                    # kill the application
                    threads.shutting_down = True
                    threads.interruptable_sleep.set()
                    # kill the thread
                    break
            except EndpointConnectionError:
                log.warning(f'Problem updating leadership of {self._app_name} as {self._device_name}', exc_info=True)
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
            # do not spin
            threads.interruptable_sleep.wait(ELECTION_UPDATE_INTERVAL_SECS)
        log.warn('No longer re-electing leadership due to shutdown.')
