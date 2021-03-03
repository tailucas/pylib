import builtins
import logging
import umsgpack
import zmq

from sentry_sdk import capture_exception
from threading import Thread
from time import sleep
# pylint: disable=no-name-in-module
from zmq.error import ZMQError, ContextTerminated, Again

# pylint: disable=relative-beyond-top-level
from .data import make_payload
from .datetime import make_timestamp


log = logging.getLogger(APP_NAME) # pylint: disable=undefined-variable


class AppPuller(Thread):

    def __init__(self, push_ip, push_port):
        super(AppPuller, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._push_ip = push_ip
        self._push_port = push_port

        self.listener = zmq_context.socket(zmq.PULL) # pylint: disable=no-member,undefined-variable
        # what to do with notifications
        self.application = zmq_context.socket(zmq.PUSH) # pylint: disable=no-member,undefined-variable

    def run(self):
        # outputs
        self.application.connect(URL_WORKER_APP) # pylint: disable=undefined-variable
        pull_address = 'tcp://{ip}:{port}'.format(ip=self._push_ip, port=self._push_port)
        try:
            log.info('Binding PULL socket on {}'.format(pull_address))
            self.listener.bind(pull_address)
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise
        log.info('Bound PULL socket on {}'.format(pull_address))
        while True:
            try:
                self.application.send_pyobj(
                    umsgpack.unpackb(
                        self.listener.recv()))
            except ContextTerminated:
                self.listener.close()
                self.application.close()
                break
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue


class DeviceActivator(Thread):

    def __init__(self, zmq_context, zmq_ipc_url, pub_ip, pub_port):
        super(DeviceActivator, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._zmq_context = zmq_context
        self._zmq_url = zmq_ipc_url
        self._pub_ip = pub_ip
        self._pub_port = pub_port

        self.listener = zmq_context.socket(zmq.PULL) # pylint: disable=no-member
        # what to do with notifications
        self.application = zmq_context.socket(zmq.PUSH) # pylint: disable=no-member

    def run(self):
        # outputs
        self.application.connect(self._zmq_url)

        # Socket to talk to the outside world
        try:
            self.listener.bind('tcp://{ip}:{port}'.format(ip=self._pub_ip, port=self._pub_port))
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise

        while True:
            try:
                event = umsgpack.unpackb(self.listener.recv())
                if 'timestamp' in event:
                    log.debug('Received timestamp {}'.format(event['timestamp']))
                    timestamp = make_timestamp(timestamp=event['timestamp'])
                else:
                    timestamp = make_timestamp()
                if 'data' not in event:
                    log.warning('Unknown event data: {}'.format(event))
                    continue
                event_data = event['data']
                if 'trigger_output' in event_data:
                    trigger_output = event_data['trigger_output']
                    output_type = trigger_output['type']
                    if output_type.lower() == 'tts':
                        if 'input_context' not in event_data:
                            log.warning('{} requested without context, ignoring.'.format(output_type))
                            continue
                        input_device_label = event_data['input_context']['device_label']
                        event_detail = ""
                        if 'event_detail' in event_data['input_context']:
                            event_detail = ' {}'.format(event_data['input_context']['event_detail'])
                        notification_message = '{}{}'.format(input_device_label, event_detail)
                        log.info("TTS '{}'".format(notification_message))
                        self.application.send_pyobj(notification_message)
                    elif output_type.lower() == 'l2ping':
                        if 'device_params' not in event_data['trigger_output']:
                            log.error('Output type {} requires parameters to be saved.'.format(output_type))
                            continue
                        self.application.send_pyobj(event_data['trigger_output']['device_params'])
                    elif output_type.lower() == 'camera':
                        log.info("Camera snapshot '{}'".format(trigger_output['device_label']))
                        trigger_output.update({'timestamp': timestamp})
                        self.application.send_pyobj(trigger_output)
                    elif output_type.lower() == 'ioboard':
                        delay = None
                        if 'trigger_duration' in event_data:
                            delay = event_data['trigger_duration']
                        # send all output activations to the relay control, which will filter accordingly
                        self.application.send_pyobj((event_data['trigger_output']['device_key'], delay))
                    else:
                        log.error('Unconfigured output type {} for input context {}'.format(output_type, event_data))
                        continue
            except ContextTerminated:
                self.listener.close()
                self.application.close()
                break
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue


class Publisher(Thread):

    def __init__(self, zmq_context, zmq_ipc_url, pub_ip, pub_port):
        super(Publisher, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._zmq_context = zmq_context
        # Socket to talk to accept samples
        self.inproc_pull = self._zmq_context.socket(zmq.PULL) # pylint: disable=no-member
        self._zmq_url = zmq_ipc_url
        self._pub_ip = pub_ip
        self._pub_port = pub_port

    def run(self):
        self.inproc_pull.bind(self._zmq_url)
        # Socket to talk to the outside world
        publisher = self._zmq_context.socket(zmq.PUB) # pylint: disable=no-member
        pub_url = 'tcp://{ip}:{port}'.format(ip=self._pub_ip, port=self._pub_port)
        try:
            log.info('Binding application PUB socket on {}'.format(pub_url))
            publisher.bind(pub_url)
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise
        log.info('Bound application PUB socket on {}'.format(pub_url))
        while True:
            try:
                data = self.inproc_pull.recv_pyobj()
                payload = make_payload(
                    timestamp=None,
                    data=data)
                # do not info on heartbeats
                if 'device_info' not in data:
                    log.debug('Publishing {} bytes on {}'.format(len(payload), pub_url))
                publisher.send(payload)
            except ContextTerminated:
                self.inproc_pull.close()
                publisher.close()
                break
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue
