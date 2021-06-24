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


log = logging.getLogger(APP_NAME) # type: ignore


class AppPuller(Thread):

    def __init__(self, push_ip, push_port):
        super(AppPuller, self).__init__(name=self.__class__.__name__)
        self.daemon = True

        self._push_ip = push_ip
        self._push_port = push_port

        self.listener = zmq_context.socket(zmq.PULL) # type: ignore
        # what to do with notifications
        self.application = zmq_context.socket(zmq.PUSH) # type: ignore

    def process_message(self):
        raise NotImplementedError

    def startup(self):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def run(self):
        self.startup()
        # outputs
        self.application.connect(URL_WORKER_APP) # type: ignore
        pull_address = f'tcp://{self._push_ip}:{self._push_port}'
        try:
            log.info(f'Binding PULL socket on {pull_address}')
            self.listener.bind(pull_address)
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise
        log.info(f'Bound PULL socket on {pull_address}')
        while True:
            try:
                self.process_message()
            except ContextTerminated:
                self.listener.close()
                self.application.close()
                self.shutdown()
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
            self.listener.bind(f'tcp://{self._pub_ip}:{self._pub_port}')
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise

        while True:
            try:
                event = umsgpack.unpackb(self.listener.recv())
                if 'timestamp' in event:
                    timestamp = event['timestamp']
                    log.debug(f'Received timestamp {timestamp}')
                    timestamp = make_timestamp(timestamp=event['timestamp'])
                else:
                    timestamp = make_timestamp()
                if 'data' not in event:
                    log.warning(f'Unknown event data: {event}')
                    continue
                event_data = event['data']
                if 'trigger_output' in event_data:
                    trigger_output = event_data['trigger_output']
                    output_type = trigger_output['type']
                    if output_type.lower() == 'tts':
                        if 'input_context' not in event_data:
                            log.warning(f'{output_type} requested without context, ignoring.')
                            continue
                        input_device_label = event_data['input_context']['device_label']
                        event_detail = ""
                        if 'event_detail' in event_data['input_context']:
                            input_context_detail = event_data['input_context']['event_detail']
                            event_detail = f' {input_context_detail}'
                        notification_message = '{input_device_label}{event_detail}'
                        log.info(f"TTS '{notification_message}'")
                        self.application.send_pyobj(notification_message)
                    elif output_type.lower() == 'l2ping':
                        if 'device_params' not in event_data['trigger_output']:
                            log.error(f'Output type {output_type} requires parameters to be saved.')
                            continue
                        self.application.send_pyobj(event_data['trigger_output']['device_params'])
                    elif output_type.lower() == 'camera':
                        device_label = trigger_output['device_label']
                        log.info(f"Camera snapshot '{device_label}'")
                        trigger_output.update({'timestamp': timestamp})
                        self.application.send_pyobj(trigger_output)
                    elif output_type.lower() == 'ioboard':
                        delay = None
                        if 'trigger_duration' in event_data:
                            delay = event_data['trigger_duration']
                        # send all output activations to the relay control, which will filter accordingly
                        self.application.send_pyobj((event_data['trigger_output']['device_key'], delay))
                    else:
                        log.error(f'Unconfigured output type {output_type} for input context {event_data}')
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
        pub_url = f'tcp://{self._pub_ip}:{self._pub_port}'
        try:
            log.info(f'Binding application PUB socket on {pub_url}')
            publisher.bind(pub_url)
        except ZMQError:
            log.exception(self.__class__.__name__)
            raise
        log.info(f'Bound application PUB socket on {pub_url}')
        while True:
            try:
                data = self.inproc_pull.recv_pyobj()
                payload = make_payload(
                    timestamp=None,
                    data=data)
                # do not info on heartbeats
                if 'device_info' not in data:
                    log.debug(f'Publishing {len(payload)} bytes on {pub_url}')
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
