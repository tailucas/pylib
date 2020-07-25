import boto3
import builtins
import logging
import logging.handlers
import os
import os.path
import sentry_sdk
import sys
import zmq

from configparser import ConfigParser
from pathlib import Path


if sys.stdout.isatty() and os.system('systemctl status app') == 0:
    print("{} is already running. Use 'systemctl stop app' to stop first.".format(APP_NAME))
    sys.exit(1)

app_path = Path(os.path.abspath(os.path.dirname(__file__)))
# set the working directory for libraries that assume this (such as PyDrive)
os.chdir(app_path.parent)

config = ConfigParser()
config.optionxform = str
config.read([os.path.join(app_path.parent, '{}.conf'.format(APP_NAME))])
builtins.DEVICE_NAME = config.get('app', 'device_name')

sentry_sdk.init(
    dsn=config.get('sentry', 'dsn'),
    integrations=SENTRY_EXTRAS
)
builtins.zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)

# shutdown flag
builtins.shutting_down = False
# threads to interrupt
builtins.interruptable_sleep = threading.Event()
# threads to nanny
builtins.threads_tracked = set()

builtins.log = logging.getLogger(APP_NAME)
# do not propagate to console logging
log.propagate = False
# DEBUG logging until startup complete
log.setLevel(logging.DEBUG)
syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
formatter = logging.Formatter('%(name)s %(threadName)s [%(levelname)s] %(message)s')
syslog_handler.setFormatter(formatter)
log.addHandler(syslog_handler)
if sys.stdout.isatty():
    log.warning("Using console logging because there is a tty.")
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)
# set up application metrics
builtins.boto3_session = boto3.Session()
builtins.app_metrics = boto3_session.client('cloudwatch')

from pylib.datetime import is_list, make_timestamp, parse_datetime
from pylib.data import make_payload
from pylib.aws.metrics import post_count_metric
from pylib.aws.swf import SWFActivityWaiter, \
    swf_exception_handler, \
    DeviceInfoActivity, \
    DeviceWorkflow
from pylib.process import SignalHandler
from pylib.threads import thread_nanny
