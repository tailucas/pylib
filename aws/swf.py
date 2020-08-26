import logging
import netifaces
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
from botoflow.exceptions import ActivityTaskFailedError, ActivityTaskTimedOutError, \
    WorkflowFailedError, WorkflowTimedOutError

from .. import process
from .. import threads
from ..bluetooth import ping_bluetooth_devices
from ..data import make_payload
from .metrics import post_count_metric


log = logging.getLogger(APP_NAME)


class SWFActivityWaiter(Thread):

    def __init__(self, zmq_ipc_url, zmq_context, event_source, output_type, workflow_starter, workflow_instance):
        super(SWFActivityWaiter, self).__init__(name=self.__class__.__name__)
        self.daemon = True
        self._event_source = event_source
        self._output_type = output_type
        self._workflow_starter = workflow_starter
        self._workflow_instance = workflow_instance
        self._zmq_url = zmq_ipc_url
        self.socket = zmq_context.socket(zmq.PUSH)

    def run(self):
        if self._workflow_instance is None:
            log.warning('No workflow instance for {} @ {}'.format(self._output_type, self._event_source))
            return
        execution_result = None
        try:
            self.socket.connect(self._zmq_url)
            try:
                log.info("Awaiting {} execution result: {}".format(
                    self._output_type,
                    self._workflow_instance.workflow_execution))
                execution_result = self._workflow_starter.wait_for_completion(self._workflow_instance, 1)
            except (WorkflowTimedOutError, WorkflowFailedError) as e:
                log.warning(
                    "Workflow {} has failed.".format(self._workflow_instance.workflow_execution),
                    exc_info=e)
            if execution_result is not None:
                self.socket.send_pyobj({self._event_source: execution_result})
        except Exception:
            log.exception(self._name)
            capture_exception()
        finally:
            self.socket.close()
        log.info('{} is done for {} with result {}'.format(self._name, self._output_type, execution_result))


def swf_exception_handler(err: Exception, tb_list: StackSummary):
    log.fatal('SWF processing exception: {} {}'.format(err, tb_list.format()))
    post_count_metric('Fatals')
    threads.shutting_down = True
    threads.interruptable_sleep.set()


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class HelloWorldActivities(object):

    @activity(version='1.0', start_to_close_timeout=5*SECONDS)
    def get_name(self):
        return APP_NAME

    @activity(version='1.1', start_to_close_timeout=5*SECONDS)
    def print_greeting(self, greeting, name):
        message = "{} {}!".format(greeting, name)
        log.info(message)
        return message


class HelloWorldWorkflow(WorkflowDefinition):

    @execute(version='1.1', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, greeting):
        name = yield HelloWorldActivities.get_name()
        with activity_options(task_list='notifier'):
            yield TTSActivity.say("Testing {}".format(name))
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
        if ping_responses is None:
            return None
        active_devices = []
        for owner, ping_response in list(ping_responses.items()):
            device_label = '{} is here.'.format(owner)
            log.info('{} {} in {}: [{}] => ({})'.format(
                self.device_type,
                owner,
                self.device_location,
                ping_response,
                device_label))
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
        self._zmq_worker = None

    @activity(version='1.1', start_to_close_timeout=5*SECONDS)
    def trigger_output(self, device_key, delay):
        try:
            # create ZMQ socket and use on the correct thread
            if (self._zmq_worker is None):
                self._zmq_worker = zmq_context.socket(zmq.PUSH)
                self._zmq_worker.connect(self._zmq_url)
            self._zmq_worker.send_pyobj((device_key, delay))
        except Exception:
            log.exception(self.__class__.__name__)
            capture_exception()
            raise

    def stop(self):
        # create ZMQ socket and use on the correct thread
        if (self._zmq_worker is not None):
            self._zmq_worker.close()


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class TTSActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url
        self._zmq_worker = None

    @activity(version='1.0', start_to_close_timeout=30*SECONDS)
    def say(self, message):
        try:
            # create ZMQ socket and use on the correct thread
            if (self._zmq_worker is None):
                self._zmq_worker = zmq_context.socket(zmq.PUSH)
                self._zmq_worker.connect(self._zmq_url)
            self._zmq_worker.send_pyobj(message)
        except Exception:
            log.exception(self.__class__.__name__)
            capture_exception()
            raise

    def stop(self):
        # create ZMQ socket and use on the correct thread
        if (self._zmq_worker is not None):
            self._zmq_worker.close()


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class SnapshotActivity(object):

    def __init__(self, zmq_url):
        self._zmq_url = zmq_url
        self._zmq_worker = None

    @activity(version='1.0', start_to_close_timeout=30*SECONDS)
    def snapshot_camera(self, device_key, camera_command):
        try:
            # create ZMQ socket and use on the correct thread
            if (self._zmq_worker is None):
                self._zmq_worker = zmq_context.socket(zmq.PUSH)
                self._zmq_worker.connect(self._zmq_url)
            self._zmq_worker.send_pyobj((device_key, camera_command))
        except Exception:
            log.exception(self.__class__.__name__)
            capture_exception()
            raise

    def stop(self):
        # create ZMQ socket and use on the correct thread
        if (self._zmq_worker is not None):
            self._zmq_worker.close()


@activities(schedule_to_start_timeout=1*MINUTES,
            start_to_close_timeout=1*MINUTES)
class DeviceInfoActivity(object):

    @activity(version='1.1', start_to_close_timeout=5*SECONDS)
    def get_ip_address(self):
        ipv4_address = None
        lan_iface = None
        default_gateway_ipv4_iface = None
        # use the gateway data to find the LAN device from which IP is determined
        default_gateway_ipv4 = netifaces.gateways()['default'][netifaces.AF_INET]
        if default_gateway_ipv4 is not None and len(default_gateway_ipv4) > 0:
            default_gateway_ipv4_address = default_gateway_ipv4[0]
            default_gateway_ipv4_iface = default_gateway_ipv4[1]
            log.info('Gateway address is {} on {}'.format(default_gateway_ipv4_address, default_gateway_ipv4_iface))
            lan_iface = default_gateway_ipv4_iface
        else:
            # go old-skool
            ifaces = netifaces.interfaces()
            # put wlan at the end
            ifaces.sort()
            for iface in ifaces:
                if iface.lower().startswith(("et", "en", "wlan")):
                    try:
                        netifaces.ifaddresses(iface)[netifaces.AF_INET]
                    except KeyError:
                        next
                    lan_iface = iface
                    break
        ipv4_address = netifaces.ifaddresses(lan_iface)[netifaces.AF_INET][0]['addr']
        log.info('Using IPv4 address {} on {}'.format(ipv4_address, lan_iface))
        return ipv4_address


class DeviceWorkflow(WorkflowDefinition):

    @execute(version='1.1', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, app):
        app_ip = None
        with activity_options(task_list=app):
            try:
                app_ip = yield DeviceInfoActivity.get_ip_address()
            except ActivityTaskTimedOutError:
                pass
        return_({app: app_ip})


class SnapshotWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, device_key, camera_command):
        response = None
        with activity_options(task_list=APP_CONFIG.get('swf_tasklist', OUTPUT_TYPE_SNAPSHOT)):
            response = yield SnapshotActivity.snapshot_camera(device_key, camera_command)
        return_(response)


class TTSWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, message):
        response = None
        with activity_options(task_list=APP_CONFIG.get('swf_tasklist', OUTPUT_TYPE_TTS)):
            response = yield TTSActivity.say(message)
        return_(response)


class IOBoardWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, device_key, delay):
        response = None
        with activity_options(task_list=APP_CONFIG.get('swf_tasklist', OUTPUT_TYPE_SWITCH)):
            response = yield IOBoardActivity.trigger_output(device_key, delay)
        return_(response)


class BluetoothWorkflow(WorkflowDefinition):

    @execute(version='1.0', execution_start_to_close_timeout=1*MINUTES)
    def execute(self, owner_device_list):
        response = None
        with activity_options(task_list=APP_CONFIG.get('swf_tasklist', OUTPUT_TYPE_BLUETOOTH)):
            response = yield BluetoothActivity.ping_bluetooth(owner_device_list)
        return_(response)