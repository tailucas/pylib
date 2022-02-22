import logging
import pika
import zmq

from datetime import datetime, timedelta
from dateutil import tz
from pika.exceptions import StreamLostError, \
    ConnectionClosedByBroker, \
    AMQPChannelError, \
    AMQPConnectionError
from random import choice
from sentry_sdk import capture_exception
from threading import Thread, Event
from time import time
from zmq.error import Again

from .app import AppThread
from .data import make_payload
from .datetime import make_timestamp, make_unix_timestamp
from .handler import exception_handler
from .rabbit import MQTopicListener, MQConnection
from .zmq import Closable

from . import threads


log = logging.getLogger(APP_NAME) # type: ignore


URL_WORKER_LEADER = 'inproc://leader'
TOPIC_PREFIX = 'leader'
ELECTION_POLL_INTERVAL_SECS = 1
ELECTION_POLL_THRESHOLD_SECS = 6
ELECTION_UPDATE_INTERVAL_SECS = ELECTION_POLL_INTERVAL_SECS * 3

ELECTION_RETRY_INTERVAL_SECS = 10
LEADERSHIP_STATUS_SECS = 60
LEADERSHIP_GRACE_PERIOD_SECS = 300


yield_to_leader_event = Event()


class Leader(MQConnection):

    def __init__(self, mq_server_address, mq_exchange_name, app_name=APP_NAME, device_name=DEVICE_NAME): # type: ignore
        MQConnection.__init__(self, mq_server_address=mq_server_address)

        self._app_name = app_name
        self._device_name = device_name

        self._mq_exchange_name = mq_exchange_name

        # listen for ongoing leader heartbeats
        self._topic_listener = MQTopicListener(
            zmq_url=URL_WORKER_LEADER,
            mq_server_address=mq_server_address,
            mq_exchange_name=self._mq_exchange_name,
            mq_topic_filter=f'event.{TOPIC_PREFIX}.#')

        # reference to start-up time
        self._last_message_time = int(time())
        self._is_leader = False
        self._elected_leader = None
        self._elected_leader_at = None
        self._signalled = False

    def close(self):
        self._topic_listener.close()
        MQConnection.close(self)

    def _log_leader(self):
        leader_name = "unknown"
        if self._elected_leader:
            leader_name = self._elected_leader
        leader_since = "unknown"
        if self._elected_leader_at:
            leader_since = self._elected_leader_at
        else:
            leader_since = make_timestamp(timestamp=self._elected_leader_at, make_string=True)
        log.info(f'Elected leader for {self._app_name} is currently {leader_name} since {leader_since}.')

    def yield_to_leader(self):
        while not threads.shutting_down:
            self._log_leader()
            yield_to_leader_event.wait(LEADERSHIP_STATUS_SECS)
            if self._signalled:
                break
        log.info(f'Acquired leadership of {self._app_name} by {self._device_name}.')

    def _setup_senders(self):
        self._mq_connection = pika.BlockingConnection(parameters=self._pika_parameters)
        mq_channel_topic = self._mq_connection.channel()
        mq_channel_topic.exchange_declare(exchange=self._mq_exchange_name, exchange_type='topic')
        self._mq_channel = mq_channel_topic

    def run(self):
        with exception_handler(closable=self, connect_url=URL_WORKER_LEADER, socket_type=zmq.PULL) as zmq_socket:
            # start getting the topic and queue info
            self._topic_listener.start()
            # set up senders
            self._setup_senders()
            while not threads.shutting_down:
                try:
                    zmq_events = zmq_socket.poll(timeout=ELECTION_POLL_INTERVAL_SECS * 1000)
                    now = int(time())
                    event = None
                    if zmq_events > 0:
                        try:
                            event = zmq_socket.recv_pyobj(zmq.NOBLOCK)
                        except Again as e:
                            log.debug(f'{e!s}')
                    message_age = now - self._last_message_time
                    event_payload = {
                        'app_name': self._app_name,
                        'device_name': self._device_name,
                        'leader_elect': self._elected_leader
                    }
                    # no leader message has arrived
                    if message_age > ELECTION_POLL_THRESHOLD_SECS:
                        log.info(f'Triggering leader election for {self._app_name} ({ELECTION_POLL_THRESHOLD_SECS}s without updates)...')
                        self._mq_channel.basic_publish(
                            exchange=self._mq_exchange_name,
                            routing_key=f'event.{TOPIC_PREFIX}.elect',
                            body=make_payload(data=event_payload))
                    if event is None:
                        continue
                    # update from an any candidate leader
                    self._last_message_time = now
                    action, data = list(event.items())[0]
                    data = data['data']
                    # leadership mode
                    partner_name = data['device_name']
                    leader_elect = data['leader_elect']
                    log.debug(f'Leadership mode {action} message: {data}')
                    if action == 'elect':
                        if self._elected_leader is None or self._elected_leader != leader_elect:
                            # make a choice
                            old_elected_leader = self._elected_leader
                            self._elected_leader = choice([self._device_name, leader_elect])
                            # do not choose None
                            if self._elected_leader is None:
                                self._elected_leader = self._device_name
                            # reduce log noise
                            if self._elected_leader != old_elected_leader:
                                log.info(f'Electing {self._elected_leader} (previously {old_elected_leader}) over leader elect {leader_elect} from {partner_name}...')
                                self._elected_leader_at = now
                            event_payload['leader_elect'] = self._elected_leader
                            self._mq_channel.basic_publish(
                                exchange=self._mq_exchange_name,
                                routing_key=f'event.{TOPIC_PREFIX}.elect',
                                body=make_payload(data=event_payload))
                        elif self._elected_leader == leader_elect and self._elected_leader == self._device_name and (now - self._elected_leader_at >= ELECTION_UPDATE_INTERVAL_SECS):
                            log.info(f'Elected {self._device_name} for {self._app_name} ({ELECTION_UPDATE_INTERVAL_SECS}s)...')
                            self._is_leader = True
                    else:
                        if self._is_leader and partner_name != self._device_name and leader_elect != self._device_name:
                            # bail the application
                            log.warning(f'Lost leadership of {self._app_name}. {partner_name} claims {leader_elect} is leader.')
                            self._is_leader = False
                            # kill the application
                            threads.shutting_down = True
                            threads.interruptable_sleep.set()
                        elif self._elected_leader is None:
                            # record the leader for logging purposes
                            log.info(f'Setting elected leader to {leader_elect} via {self._device_name}.')
                            self._elected_leader = leader_elect
                            self._elected_leader_at = now
                    # send hearbeats
                    if self._is_leader:
                        log.debug(f'Sending leadership notification: {event_payload}')
                        self._mq_channel.basic_publish(
                            exchange=self._mq_exchange_name,
                            routing_key=f'event.{TOPIC_PREFIX}.notify',
                            body=make_payload(data=event_payload))
                        if not self._signalled:
                            log.info(f'Signalling application to finish startup...')
                            self._signalled = True
                            yield_to_leader_event.set()
                    else:
                        continue
                    # prevent spinning on messages
                    threads.interruptable_sleep.wait(ELECTION_POLL_INTERVAL_SECS)
                except (StreamLostError, AMQPConnectionError) as e:
                    if not threads.shutting_down:
                        raise e
                except (ConnectionClosedByBroker, AMQPChannelError) as ce:
                    if not threads.shutting_down:
                        backoff = 10
                        log.warning(f'{ce!s}. Retrying connection setup after {backoff}s backoff...')
                        threads.interruptable_sleep.wait(backoff)
