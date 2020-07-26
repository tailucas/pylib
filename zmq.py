import builtins
import logging
import umsgpack
import zmq

from sentry_sdk import capture_exception
from threading import Thread
from time import sleep
from zmq.error import ZMQError, ContextTerminated, Again

from .data import make_payload
from .datetime import make_timestamp

log = logging.getLogger(APP_NAME)

builtins.URL_WORKER_UPLOADER = 'inproc://uploader'
builtins.URL_WORKER_APP = 'inproc://app'


class DeviceActivator(Thread):

    def __init__(self, zmq_context, zmq_ipc_url, pub_ip, pub_port):
        super(DeviceActivator, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._zmq_context = zmq_context
        self._zmq_url = zmq_ipc_url
        self._pub_ip = pub_ip
        self._pub_port = pub_port

        self.listener = zmq_context.socket(zmq.PULL)
        # what to do with notifications
        self.application = zmq_context.socket(zmq.PUSH)

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
                            log.error('Output type requires parameters to be saved.'.format(output_type))
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


class Uploader(Thread):

    def __init__(self, zmq_context, zmq_ipc_url, pub_ip, pub_port):
        super(Uploader, self).__init__()
        self.daemon = True
        self._zmq_context = zmq_context
        # Socket to talk to accept samples
        self.inproc_pull = self._zmq_context.socket(zmq.PULL)
        self._zmq_url = zmq_ipc_url
        self._pub_ip = pub_ip
        self._pub_port = pub_port

    def run(self):
        self.inproc_pull.bind(self._zmq_url)
        # Socket to talk to the outside world
        publisher = self._zmq_context.socket(zmq.PUB)
        try:
            publisher.bind('tcp://{ip}:{port}'.format(ip=self._pub_ip, port=self._pub_port))
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise

        while True:
            try:
                publisher.send(make_payload(
                    timestamp=None,
                    data=self.inproc_pull.recv_pyobj()))
            except ContextTerminated:
                self.inproc_pull.close()
                publisher.close()
                break
            except Exception:
                log.exception(self.__class__.__name__)
                capture_exception()
                sleep(1)
                continue
