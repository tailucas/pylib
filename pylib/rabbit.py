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
from zmq.error import ZMQError

from . import threads

from .app import AppThread
from .handler import exception_handler
from .zmq import Closable


log = logging.getLogger(APP_NAME) # type: ignore


class MQConnection(AppThread, Closable):
    def __init__(self, mq_server_address):
        AppThread.__init__(self, name=self.__class__.__name__)
        Closable.__init__(self)

        self.processor = self.get_socket(zmq.PUSH)

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

        self._mq_connection = None
        self._mq_channel = None

    def close(self):
        if self._mq_channel:
            try:
                self._mq_channel.stop_consuming()
            except Exception:
                pass
        if self._mq_connection:
            try:
                self._mq_connection.close()
            except Exception:
                pass
        Closable.close(self)


class MQListener(MQConnection):

    def __init__(self, zmq_url, mq_server_address):
        MQConnection.__init__(self, mq_server_address=mq_server_address)
        self._zmq_url = zmq_url

    def _setup_channel(self):
        raise NotImplementedError()

    # noinspection PyBroadException
    def run(self):
        self.processor.connect(self._zmq_url)
        with exception_handler(closable=self):
            while not threads.shutting_down:
                try:
                    self._mq_connection = pika.BlockingConnection(parameters=self._pika_parameters)
                    self._mq_channel = self._setup_channel()
                    log.debug(f'Ready for RabbitMQ messages.')
                    self._mq_channel.start_consuming()
                    log.debug(f'RabbitMQ listener has finished.')
                except (StreamLostError, AMQPConnectionError) as e:
                    if not threads.shutting_down:
                        raise e
                except (ConnectionClosedByBroker, AMQPChannelError) as ce:
                    if not threads.shutting_down:
                        backoff = 10
                        log.warning(f'{ce!s}. Retrying connection setup after {backoff}s backoff...')
                        threads.interruptable_sleep.wait(backoff)


class MQTopicListener(MQListener):

    def __init__(self, zmq_url, mq_server_address, mq_exchange_name, mq_topic_filter='#'):
        MQListener.__init__(self, zmq_url=zmq_url, mq_server_address=mq_server_address)

        self._mq_exchange_type = 'topic'
        self._mq_exchange_name = mq_exchange_name
        self._mq_topic_filter = mq_topic_filter

    def _setup_channel(self):
        mq_channel = self._mq_connection.channel()
        mq_channel.exchange_declare(exchange=self._mq_exchange_name, exchange_type=self._mq_exchange_type)
        mq_result = mq_channel.queue_declare('', exclusive=True)
        mq_queue_name = mq_result.method.queue
        log.info(f'Using RabbitMQ server(s) {self._mq_server_list} using {self._mq_exchange_type} exchange {self._mq_exchange_name} and queue {mq_queue_name}.')
        mq_channel.queue_bind(
            exchange=self._mq_exchange_name,
            queue=mq_queue_name,
            routing_key=self._mq_topic_filter)
        mq_channel.basic_consume(
            queue=mq_queue_name,
            on_message_callback=self.callback,
            auto_ack=True)
        return mq_channel

    def callback(self, ch, method, properties, body):
        topic = method.routing_key
        log.debug(f'[{topic}]: {body}')
        topic_parts = topic.split('.')
        if len(topic_parts) < 3:
            log.warning(f'Ignoring non-routable message from topic [{topic}] due to unsufficient topic parts.')
            return
        if 'heartbeat' not in topic:
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
            if not threads.shutting_down:
                raise e


class MQQueueListener(MQListener):

    def __init__(self, zmq_url, mq_server_address, mq_queue_name, ack_linger_secs=0):
        MQListener.__init__(self, zmq_url=zmq_url, mq_server_address=mq_server_address)

        self._mq_queue_name = mq_queue_name
        self._ack_linger_secs = ack_linger_secs

    def _setup_channel(self):
        mq_channel = self._mq_connection.channel()
        mq_result = mq_channel.queue_declare(queue=self._mq_queue_name, durable=True)
        mq_queue_name = mq_result.method.queue
        log.info(f'Using RabbitMQ server(s) {self._mq_server_list} using queue {mq_queue_name}.')
        mq_channel.basic_qos(prefetch_count=1)
        mq_channel.basic_consume(queue=self._mq_queue_name, on_message_callback=self.callback)
        return ('queue', mq_channel)

    def callback(self, ch, method, properties, body):
        self._message_counter += 1

        device_event = None
        try:
            device_event = msgpack.unpackb(body)
        except UnpackException:
            log.exception('Bad message: {}'.format(body))
            return
        try:
            self.processor.send_pyobj({self._mq_queue_name: device_event})
        except Exception as e:
            if not threads.shutting_down:
                raise e

        # linger acknowledgement
        if self._ack_linger_secs > 0:
            threads.interruptable_sleep.wait(self._ack_linger_secs)

        ch.basic_ack(delivery_tag=method.delivery_tag)
