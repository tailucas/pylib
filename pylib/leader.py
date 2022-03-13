import logging
import pika
import zmq

from pika.exceptions import StreamLostError, \
    ConnectionClosedByBroker, \
    AMQPChannelError, \
    AMQPConnectionError
from random import choice
from time import time
from zmq.error import Again

from .data import make_payload
from .datetime import make_timestamp, make_unix_timestamp
from .handler import exception_handler
from .rabbit import MQTopicListener, MQConnection

from . import threads


log = logging.getLogger(APP_NAME) # type: ignore


URL_WORKER_LEADER = 'inproc://leader'
TOPIC_PREFIX = 'leader'
ELECTION_POLL_INTERVAL_SECS = 5
ELECTION_UPDATE_INTERVAL_SECS = 10
ELECTION_POLL_THRESHOLD_SECS = 20
LEADERSHIP_STATUS_SECS = 60


class Leader(MQConnection):

    def __init__(self, mq_server_address, mq_exchange_name, app_name=APP_NAME, device_name=DEVICE_NAME): # type: ignore
        MQConnection.__init__(self, mq_server_address=mq_server_address)

        self._app_name = app_name
        self._device_name = device_name

        self._running = True

        self._mq_exchange_name = mq_exchange_name

        # listen for ongoing leader heartbeats
        self._topic_listener = MQTopicListener(
            zmq_url=URL_WORKER_LEADER,
            mq_server_address=mq_server_address,
            mq_exchange_name=self._mq_exchange_name,
            mq_topic_filter=f'event.{TOPIC_PREFIX}.#')

        # reference to start-up time
        self._last_leader_message_time = int(time())
        self._is_leader = False
        self._elected_leader = None
        self._elected_leader_at = None
        self._signalled = False

    def close(self):
        self._running = False
        self._topic_listener.close()
        MQConnection.close(self)

    def _log_leader(self):
        leader_name = "unknown"
        if self._elected_leader:
            leader_name = self._elected_leader
        leader_since = "unknown"
        if self._elected_leader_at:
            leader_since = make_timestamp(timestamp=self._elected_leader_at, make_string=True)
        log.info(f'Elected leader for {self._app_name} is currently {leader_name} since {leader_since}.')

    def yield_to_leader(self):
        while not threads.shutting_down:
            self._log_leader()
            threads.interruptable_sleep.wait(LEADERSHIP_STATUS_SECS)
            if self._signalled:
                break
        if threads.shutting_down:
            raise RuntimeWarning("Shutting down...")
        log.info(f'Acquired leadership of {self._app_name} by {self._device_name}.')

    def _setup_senders(self):
        self._mq_connection = pika.BlockingConnection(parameters=self._pika_parameters)
        self._mq_channel = self._mq_connection.channel()
        self._mq_channel.exchange_declare(exchange=self._mq_exchange_name, exchange_type='topic')

    def run(self):
        with exception_handler(closable=self, connect_url=URL_WORKER_LEADER, socket_type=zmq.PULL, and_raise=False, shutdown_on_error=True) as zmq_socket:
            # set up senders
            try:
                self._setup_senders()
            except AMQPConnectionError as e:
                raise ResourceWarning('Leader election failure at startup.') from e
            # start getting the topic and queue info
            self._topic_listener.start()
            while self._running:
                zmq_events = zmq_socket.poll(timeout=ELECTION_POLL_INTERVAL_SECS * 1000)
                now = int(time())
                event = None
                if zmq_events > 0:
                    try:
                        event = zmq_socket.recv_pyobj(zmq.NOBLOCK)
                    except Again as e:
                        log.debug(f'{e!s}')
                event_payload = {
                    'app_name': self._app_name,
                    'device_name': self._device_name,
                    'leader_elect': self._elected_leader
                }
                leader_message_age = now - self._last_leader_message_time
                # no message in this interval
                if event is None:
                    mode = 'notify'
                    if leader_message_age >= ELECTION_POLL_THRESHOLD_SECS or self._elected_leader is None:
                        log.info(f'Triggering leader election for {self._app_name} ({leader_message_age}s without updates, leader is {self._elected_leader})...')
                        # volunteer self if not already elected
                        mode = 'elect'
                        event_payload['leader_elect'] = self._device_name
                    log.debug(f'Sending {mode} message (leader message age is {leader_message_age}, leader? {self._is_leader})')
                    self._mq_channel.basic_publish(
                        exchange=self._mq_exchange_name,
                        routing_key=f'event.{TOPIC_PREFIX}.{mode}',
                        body=make_payload(data=event_payload))
                    # nothing to further to process
                    continue
                action, data = list(event.items())[0]
                data = data['data']
                # leadership mode
                partner_name = data['device_name']
                leader_elect = data['leader_elect']
                log.debug(f'Leadership mode {action} message: {data}')
                if action == 'elect':
                    self._elected_leader_at = now
                old_elected_leader = self._elected_leader
                if self._elected_leader is None:
                    if leader_elect is None:
                        log.info(f'{partner_name} has no leader. Setting elected leader to {self._device_name}.')
                        self._elected_leader = self._device_name
                    else:
                        log.info(f'{partner_name} elects {leader_elect}. Elected leader is {self._elected_leader}.')
                        self._elected_leader = leader_elect
                elif self._elected_leader == leader_elect:
                    if self._elected_leader == partner_name:
                        self._last_leader_message_time = now
                elif self._elected_leader != leader_elect:
                    # make a choice as a tie breaker
                    self._elected_leader = choice([self._device_name, leader_elect])
                    # do not choose None
                    if self._elected_leader is None:
                        self._elected_leader = self._device_name
                # if a change happened, announce it
                if self._elected_leader != old_elected_leader:
                    log.info(f'{partner_name} elects {leader_elect}. Choosing {self._elected_leader} (previously {old_elected_leader}).')
                    log.debug(f'Sending election notification: {event_payload}')
                    event_payload['leader_elect'] = self._elected_leader
                    self._mq_channel.basic_publish(
                        exchange=self._mq_exchange_name,
                        routing_key=f'event.{TOPIC_PREFIX}.elect',
                        body=make_payload(data=event_payload))
                    # process this right away
                    continue
                if self._elected_leader_at is not None:
                    elected_since = now - self._elected_leader_at
                    if not self._is_leader and self._elected_leader == leader_elect and self._elected_leader == self._device_name and elected_since >= ELECTION_UPDATE_INTERVAL_SECS:
                        log.info(f'Elected {self._device_name} as {self._app_name} (after {elected_since}s)...')
                        self._is_leader = True
                if self._is_leader:
                    if leader_elect != self._device_name:
                        raise ResourceWarning(f'{partner_name} elects {leader_elect}. Lost leadership of {self._app_name}.')
                    elif not self._signalled:
                            log.info(f'Signalling application to finish startup...')
                            self._signalled = True
                            threads.interruptable_sleep.set()
            log.info('Leader election stopped.')
