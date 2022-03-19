import inspect
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
from zmq.error import ZMQError

from . import threads

from .app import AppThread
from .handler import exception_handler
from .zmq import Closable


# Reduce Sentry noise from pika loggers
ignore_logger('pika.adapters.base_connection')
ignore_logger('pika.adapters.blocking_connection')
ignore_logger('pika.adapters.utils.connection_workflow')
ignore_logger('pika.adapters.utils.io_services_utils')
ignore_logger('pika.callback')
ignore_logger('pika.channel')
ignore_logger('pika.connection')


log = logging.getLogger(APP_NAME) # type: ignore


class MQConnection(AppThread, Closable):
    def __init__(self, mq_server_address, mq_exchange_name, mq_topic_filter='#', mq_exchange_type='topic'):
        AppThread.__init__(self, name=self.__class__.__name__)
        Closable.__init__(self)

        if isinstance(mq_server_address, str):
            self._mq_server_list = [mq_server_address]
        elif isinstance(mq_server_address, list):
            self._mq_server_list = mq_server_address
        else:
            raise AssertionError(f'Unsupported argument type: {mq_server_address}')

        pika_parameters = list()
        for source in self._mq_server_list:
            pika_parameters.append(pika.ConnectionParameters(host=source))
        self._pika_parameters = tuple(pika_parameters)

        self._mq_exchange_name = mq_exchange_name
        self._mq_topic_filter = mq_topic_filter
        self._mq_exchange_type = mq_exchange_type

        self._mq_connection = None
        self._mq_channel = None
        self._mq_queue_name = None

    def _setup_channel(self):
        self._mq_connection = pika.BlockingConnection(parameters=self._pika_parameters)
        self._mq_channel = self._mq_connection.channel()
        self._mq_channel.exchange_declare(exchange=self._mq_exchange_name, exchange_type=self._mq_exchange_type)
        mq_result = self._mq_channel.queue_declare('', exclusive=True)
        self._mq_queue_name = mq_result.method.queue
        log.info(f'Using RabbitMQ server(s) {self._mq_server_list} using {self._mq_exchange_type} exchange {self._mq_exchange_name} and queue {self._mq_queue_name}.')

    def stop(self):
        if self._mq_channel:
            log.info(f'Stopping RabbitMQ channel for {self.name}...')
            try:
                self._mq_channel.stop_consuming()
            except Exception:
                log.debug(self.__class__.__name__, exc_info=True)
        if self._mq_connection:
            log.info(f'Closing RabbitMQ connection for {self.name}...')
            try:
                self._mq_connection.close()
            except Exception:
                log.debug(self.__class__.__name__, exc_info=True)
        Closable.close(self)


class ZMQListener(MQConnection):

    def __init__(self, zmq_url, mq_server_address, mq_exchange_name, mq_topic_filter, mq_exchange_type):
        MQConnection.__init__(
            self,
            mq_server_address=mq_server_address,
            mq_exchange_name=mq_exchange_name,
            mq_topic_filter=mq_topic_filter,
            mq_exchange_type=mq_exchange_type)
        self.processor = self.get_socket(zmq.PUSH)
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
        self.processor.connect(self._zmq_url)
        with exception_handler(closable=self, and_raise=False, shutdown_on_error=True):
            self._setup_channel()
            log.info(f'Ready for RabbitMQ messages in {self.name}.')
            try:
                self._mq_channel.start_consuming()
            except (ConnectionClosedByBroker, StreamLostError) as e:
                # handled error
                raise ResourceWarning('Consumer interrupted.') from e
            except Exception as e:
                log.debug(self.__class__.__name__, exc_info=True)
                if not threads.shutting_down:
                    raise e
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
