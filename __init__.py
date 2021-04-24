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
from onepasswordconnectsdk.client import (
    Client,
    new_client_from_environment
)

if sys.stdout.isatty() and os.system('systemctl status app') == 0:
    print("{} is already running. Use 'systemctl stop app' to stop first.".format(APP_NAME))
    sys.exit(1)

# use parent of this module's top-level __init__.py
app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
# set the working directory for libraries that assume this (such as PyDrive)
os.chdir(app_path)
app_config = ConfigParser()
app_config.optionxform = str
app_config.read([os.path.join(app_path, '{}.conf'.format(APP_NAME))])

sentry_sdk.init(
    dsn=app_config.get('sentry', 'dsn'),
    integrations=SENTRY_EXTRAS
)

zmq_context = zmq.Context()
zmq_context.setsockopt(zmq.LINGER, 0)

log = logging.getLogger(APP_NAME)

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

# credential server
creds_client: Client = new_client_from_environment(url=app_config.get('app', 'creds_server'))

# update builtins
builtins.APP_CONFIG = app_config
builtins.DEVICE_NAME = app_config.get('app', 'device_name')
builtins.log = log
builtins.creds = creds_client
builtins.creds_vault_id = app_config.get('app', 'creds_vault_id')
builtins.zmq_context = zmq_context
builtins.URL_WORKER_APP = 'inproc://app'
builtins.URL_WORKER_PUBLISHER = 'inproc://publisher'
