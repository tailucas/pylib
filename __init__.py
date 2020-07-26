import boto3
import botocore
import builtins
import logging
import logging.handlers
import os
import os.path
import sentry_sdk
import sys
import threading
import zmq

from configparser import ConfigParser
from pathlib import Path


if sys.stdout.isatty() and os.system('systemctl status app') == 0:
    print("{} is already running. Use 'systemctl stop app' to stop first.".format(APP_NAME))
    sys.exit(1)

app_path = Path(os.path.abspath(os.path.dirname(__file__)))
# set the working directory for libraries that assume this (such as PyDrive)
os.chdir(app_path.parent)

builtins.APP_CONFIG = ConfigParser()
APP_CONFIG.optionxform = str
APP_CONFIG.read([os.path.join(app_path.parent, '{}.conf'.format(APP_NAME))])
builtins.DEVICE_NAME = APP_CONFIG.get('app', 'device_name')

sentry_sdk.init(
    dsn=APP_CONFIG.get('sentry', 'dsn'),
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
builtins.APP_METRICS = boto3_session.client('cloudwatch')
builtins.boto_session = botocore.session.Session(profile=APP_CONFIG.get('botoflow', 'profile'))
builtins.swf_region = APP_CONFIG.get('botoflow', 'region')
builtins.swf_domain = APP_CONFIG.get('botoflow', 'domain')
