import logging
import msgpack
import pika
import zmq

from msgpack.exceptions import UnpackException
from pika.exceptions import StreamLostError, \
    ConnectionClosedByBroker, \
    AMQPChannelError, \
    AMQPConnectionError
from sentry_sdk.integrations.logging import ignore_logger

from . import threads

from .app import AppThread
from .data import make_payload
from .datetime import make_timestamp, make_unix_timestamp
from .handler import exception_handler


# Reduce Sentry noise from pika loggers
ignore_logger('pika.adapters.base_connection')
ignore_logger('pika.adapters.blocking_connection')
ignore_logger('pika.adapters.utils.connection_workflow')
ignore_logger('pika.adapters.utils.io_services_utils')
ignore_logger('pika.callback')
ignore_logger('pika.channel')
ignore_logger('pika.connection')


log = logging.getLogger(APP_NAME)  # type: ignore


BLOCKED_CONNECTION_TIMEOUT = 5
PUBLISH_RETRIES = 2


class MQConnection(AppThread):
    def __init__(self, mq_server_address, mq_exchange_name, mq_topic_filter='#', mq_exchange_type='topic', mq_arguments=None):
        AppThread.__init__(self, name=self.__class__.__name__)

        if isinstance(mq_server_address, str):
            self._mq_server_list = [mq_server_address]
        elif isinstance(mq_server_address, list):
            self._mq_server_list = mq_server_address
        else:
            raise AssertionError(f'Unsupported argument type: {mq_server_address}')

        pika_parameters = list()
        for source in self._mq_server_list:
            pika_parameters.append(pika.ConnectionParameters(
                host=source,
                blocked_connection_timeout=BLOCKED_CONNECTION_TIMEOUT))
        self._pika_parameters = tuple(pika_parameters)

        self._mq_exchange_name = mq_exchange_name
        self._mq_topic_filter = mq_topic_filter
        self._mq_exchange_type = mq_exchange_type
        self._mq_arguments = mq_arguments

        self._mq_connection = None
        self._mq_channel = None
        self._mq_queue_name = None

    def _basic_publish(self, routing_key, event_payload, close_channel=False, close_connection=False):
        success = False
        tries = 1
        while tries <= PUBLISH_RETRIES:
            try:
                self._setup_channel()
            except AMQPConnectionError as e:
                raise ResourceWarning('Problem setting up connection or channel.') from e
            try:
                self._mq_channel.basic_publish(
                    exchange=self._mq_exchange_name,
                    routing_key=routing_key,
                    body=make_payload(data=event_payload))
                success = True
                # exit loop
                break
            except StreamLostError as e:
                # try again
                if tries < PUBLISH_RETRIES:
                    log.warning(f'Retrying on lost stream during publish: {e!s}')
                    continue
                else:
                    raise RuntimeWarning('Publish failure after retry.') from e
            except ConnectionClosedByBroker as e:
                raise ResourceWarning() from e
            finally:
                tries += 1
                if close_channel or not success:
                    log.debug(f'Closing potentially stale channel (successful attempt? {success})...')
                    self._close_channel()
                    if close_connection or not success:
                        log.debug(f'Closing potentially stale connection (successful attempt? {success})...')
                        self._close_connection()
        if not success:
            raise AssertionError('No success after publish attempt.')

    def _setup_connection(self):
        if self._mq_connection is None or self._mq_connection.is_closed:
            self._mq_connection = pika.BlockingConnection(parameters=self._pika_parameters)

    def _setup_channel(self):
        self._setup_connection()
        if self._mq_channel is None or self._mq_channel.is_closed:
            self._mq_channel = self._mq_connection.channel()
            self._mq_channel.exchange_declare(exchange=self._mq_exchange_name, exchange_type=self._mq_exchange_type, arguments=self._mq_arguments)
            mq_result = self._mq_channel.queue_declare('', exclusive=True)
            self._mq_queue_name = mq_result.method.queue
            log.info(f'Using RabbitMQ server(s) {self._mq_server_list} using {self._mq_exchange_type} exchange {self._mq_exchange_name} and queue {self._mq_queue_name}.')

    def _close_connection(self):
        if self._mq_connection:
            log.info(f'Closing RabbitMQ connection for {self.name}...')
            try:
                self._mq_connection.close()
            except Exception:
                log.debug(self.__class__.__name__, exc_info=True)

    def _close_channel(self):
        if self._mq_channel:
            log.info(f'Stopping RabbitMQ channel for {self.name}...')
            try:
                self._mq_channel.stop_consuming()
            except Exception:
                log.debug(self.__class__.__name__, exc_info=True)

    def stop(self):
        self._close_channel()
        self._close_connection()


class ZMQListener(MQConnection):

    def __init__(self, zmq_url, mq_server_address, mq_exchange_name, mq_topic_filter, mq_exchange_type):
        MQConnection.__init__(
            self,
            mq_server_address=mq_server_address,
            mq_exchange_name=mq_exchange_name,
            mq_topic_filter=mq_topic_filter,
            mq_exchange_type=mq_exchange_type)
        self._zmq_url = zmq_url

    def _setup_channel(self):
        MQConnection._setup_channel(self)
        self._mq_channel.queue_bind(
            exchange=self._mq_exchange_name,
            queue=self._mq_queue_name,
            routing_key=self._mq_topic_filter)
        self._mq_channel.basic_consume(
            queue=self._mq_queue_name,
            on_message_callback=self.callback,
            auto_ack=True)

    # noinspection PyBroadException
    def run(self):
        with exception_handler(connect_url=self._zmq_url, and_raise=False, shutdown_on_error=True) as zmq_socket:
            self.processor = zmq_socket
            try:
                self._setup_channel()
                log.info(f'Ready for RabbitMQ messages in {self.name}.')
                self._mq_channel.start_consuming()
            except (AMQPConnectionError, ConnectionClosedByBroker, StreamLostError) as e:
                # handled error due to already shutting down
                raise ResourceWarning('Consumer interrupted.') from e
            finally:
                log.info(f'RabbitMQ listener for {self.name} has finished.')

    def callback(self, ch, method, properties, body):
        topic = method.routing_key
        log.debug(f'[{topic}]: {body}')
        topic_parts = topic.split('.')
        if len(topic_parts) < 3:
            log.warning(f'Ignoring non-routable message from topic [{topic}] due to unsufficient topic parts.')
            return
        if topic_parts[1] not in ['heartbeat', 'leader']:
            log.info(f'Device event on topic [{topic}]')
        device_event = None
        try:
            device_event = msgpack.unpackb(body)
        except UnpackException:
            log.exception('Bad message: {}'.format(body))
            return
        try:
            self.processor.send_pyobj({topic_parts[2]: device_event})
        except Exception as e:
            log.debug(self.__class__.__name__, exc_info=True)
            if not threads.shutting_down:
                raise e


class RabbitMQRelay(AppThread):

    def __init__(self, zmq_url, mq_server_address, mq_exchange_name, mq_topic_filter, mq_exchange_type):
        AppThread.__init__(self, name=self.__class__.__name__)
        self._source_zmq_url = zmq_url
        self._source_socket_type = zmq.PULL

        self._mq_config_server = mq_server_address
        self._mq_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self._mq_config_server,
                blocked_connection_timeout=BLOCKED_CONNECTION_TIMEOUT))
        self._mq_channel = self._mq_connection.channel()
        self._mq_config_exchange = mq_exchange_name
        self._mq_exchange_type = mq_exchange_type
        self._mq_channel.exchange_declare(exchange=self._mq_config_exchange, exchange_type=self._mq_exchange_type)
        self._mq_device_topic = mq_topic_filter

    @property
    def device_topic(self):
        return self._mq_device_topic

    def close(self):
        self._mq_connection.close()

    def process_message(self, zmq_socket):
        event_topic, event_payload = zmq_socket.recv_pyobj()
        try:
            self._mq_channel.basic_publish(
                exchange=self._mq_config_exchange,
                routing_key=event_topic,
                body=make_payload(data=event_payload))
        except (ConnectionClosedByBroker, StreamLostError) as e:
            raise ResourceWarning() from e

    def startup(self):
        log.info(f'Using RabbitMQ server at {self._mq_config_server} with {self._mq_exchange_type} ({self._mq_device_topic}) exchange {self._mq_config_exchange}.')

    def run(self):
        self.startup()
        with exception_handler(connect_url=self._source_zmq_url, socket_type=self._source_socket_type, and_raise=False, shutdown_on_error=True) as zmq_socket:
            while not threads.shutting_down:
                self.process_message(zmq_socket=zmq_socket)
