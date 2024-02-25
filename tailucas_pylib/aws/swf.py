import logging
import zmq

from sentry_sdk import capture_exception
from threading import Thread
from traceback import StackSummary
from botoflow import activity, \
    activities, \
    execute, \
    return_, \
    WorkflowDefinition
from botoflow.options import activity_options
from botoflow.constants import SECONDS, MINUTES
from botocore.exceptions import EndpointConnectionError as bcece
from botoflow.exceptions import ActivityTaskFailedError, ActivityTaskTimedOutError, \
    WorkflowFailedError, WorkflowTimedOutError

from .metrics import post_count_metric

from .. import threads
from ..bluetooth import ping_bluetooth_devices
from ..data import make_payload
from ..handler import exception_handler


log = logging.getLogger(APP_NAME)  # type: ignore


class SWFActivityWaiter(Thread):

    def __init__(self, zmq_ipc_url, event_source, output_type, workflow_starter, workflow_instance):
        Thread.__init__(self, name=self.__class__.__name__)
        self.daemon = True
        self._event_source = event_source
        self._output_type = output_type
        self._workflow_starter = workflow_starter
        self._workflow_instance = workflow_instance
        self._zmq_url = zmq_ipc_url

    def run(self):
        if self._workflow_instance is None:
            log.warning(f'No workflow instance for {self._output_type} @ {self._event_source}')
            return
        execution_result = None
        with exception_handler(connect_url=self._zmq_url, socket_type=zmq.PUSH, and_raise=False) as zmq_socket:
            try:
                log.info(f"Awaiting {self._output_type} execution result: {self._workflow_instance.workflow_execution}")
                execution_result = self._workflow_starter.wait_for_completion(self._workflow_instance, 1)
            except (WorkflowTimedOutError, WorkflowFailedError):
                log.warning(f'Workflow {self._workflow_instance.workflow_execution} has failed.', exc_info=True)
            if execution_result is not None:
                zmq_socket.send_pyobj({self._event_source: execution_result})
        message = f'Workflow is done for {self._output_type} with result {execution_result}'
        if execution_result:
            log.info(message)
        else:
            log.warning(message)


def swf_exception_handler(err: Exception, tb_list: StackSummary):
    try:
        raise err
    except bcece:
        log.warning(f'SWF', exc_info=True)
    except Exception:
        log.exception('SWF')
        capture_exception()
        post_count_metric('Fatals')
    finally:
        threads.shutting_down = True
        threads.interruptable_sleep.set()


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class HelloWorldActivities(object):

    @activity(version='1.0', start_to_close_timeout=5*SECONDS)
    def get_name(self):
        return APP_NAME # type: ignore

    @activity(version='1.1', start_to_close_timeout=5*SECONDS)
    def print_greeting(self, greeting, name):
        message = f"{greeting} {name}!"
        log.info(message)
        return message


class HelloWorldWorkflow(WorkflowDefinition):

    @execute(version='1.1', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, greeting):
        name = yield HelloWorldActivities.get_name()
        with activity_options(task_list='notifier'):
            yield TTSActivity.say(f"Testing {name}")
        response = yield HelloWorldActivities.print_greeting(greeting, name)
        return_(response)


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class BluetoothActivity(object):

    def __init__(self, device_key, device_type, device_location):
        super().__init__()
        self.device_key = device_key
        self.device_type = device_type
        self.device_location = device_location

    @activity(version='1.0', start_to_close_timeout=20*SECONDS)
    def ping_bluetooth(self, owner_device_list):
        ping_responses = ping_bluetooth_devices(owner_device_list)
        log.info(f'{self.device_type} {owner_device_list!s} in {self.device_location} returns {ping_responses!s}...')
        if ping_responses is None:
            return None
        active_devices = []
        for owner, ping_response in list(ping_responses.items()):
            device_label = f'{owner} is here.'
            log.info(f'{self.device_type} {owner} in {self.device_location}: [{ping_response}] => ({device_label})')
            active_devices.append({
                    'device_key': self.device_key,
                    'device_type': self.device_type,
                    'device_location': self.device_location,
                    'device_label': device_label})
        return make_payload(
            timestamp=None,
            data={'active_devices': active_devices},
            msgpack=False)


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class IOBoardActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url

    @activity(version='1.1', start_to_close_timeout=5*SECONDS)
    def trigger_output(self, device_key, duration):
        with exception_handler(connect_url=self._zmq_url, socket_type=zmq.PUSH, and_raise=False) as zmq_socket:
            zmq_socket.send_pyobj((device_key, duration))


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class TTSActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url

    @activity(version='1.0', start_to_close_timeout=30*SECONDS)
    def say(self, message):
        with exception_handler(connect_url=self._zmq_url, socket_type=zmq.PUSH, and_raise=False) as zmq_socket:
            zmq_socket.send_pyobj(message)


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class SnapshotActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url

    @activity(version='1.0', start_to_close_timeout=30*SECONDS)
    def snapshot_camera(self, device_key, device_label, camera_config):
        with exception_handler(connect_url=self._zmq_url, socket_type=zmq.PUSH, and_raise=False) as zmq_socket:
            zmq_socket.send_pyobj((device_key, device_label, camera_config))


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class ImageProcessActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url

    @activity(version='1.0', start_to_close_timeout=30*SECONDS)
    def image_process_camera(self, device_key, device_label, camera_config, snapshot_processor_address):
        with exception_handler(connect_url=self._zmq_url, socket_type=zmq.PUSH, and_raise=False) as zmq_socket:
            zmq_socket.send_pyobj((device_key, device_label, camera_config, snapshot_processor_address))


class ImageProcessWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app, device_key, device_label, camera_config, snapshot_processor_address):
        response = None
        with activity_options(task_list=app):
            response = yield ImageProcessActivity.image_process_camera(device_key, device_label, camera_config, snapshot_processor_address)
        return_(response)


class SnapshotWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app, device_key, device_label, camera_config):
        response = None
        with activity_options(task_list=app):
            response = yield SnapshotActivity.snapshot_camera(device_key, device_label, camera_config)
        return_(response)


class TTSWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app, message):
        response = None
        with activity_options(task_list=app):
            response = yield TTSActivity.say(message)
        return_(response)


class IOBoardWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app, device_key, duration=None):
        response = None
        with activity_options(task_list=app):
            response = yield IOBoardActivity.trigger_output(device_key, duration)
        return_(response)


class BluetoothWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app, owner_device_list):
        response = None
        with activity_options(task_list=app):
            response = yield BluetoothActivity.ping_bluetooth(owner_device_list)
        return_(response)