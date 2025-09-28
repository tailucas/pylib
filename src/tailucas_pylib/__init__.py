from configparser import ConfigParser
from logging import Logger, Handler
from os import getenv
from pathlib import Path

import locale
import logging.handlers
import os
import os.path
import socket
import sys

from locale import Error as LocaleError
from urllib.parse import urlparse

from .creds import Creds

APP_NAME = getenv("APP_NAME", "test")
WORK_DIR = getenv("WORK_DIR", "/opt/app")
DEVICE_NAME = getenv("DEVICE_NAME")
DEVICE_NAME_BASE = None

log: Logger = logging.getLogger(APP_NAME)
try:
    log_level_name = os.environ["LOG_LEVEL"]
    log.setLevel(log_level_name.upper())
except KeyError:
    pass

log_handler: Handler = None  # type: ignore
syslog_server = None
try:
    syslog_address = os.environ["SYSLOG_ADDRESS"]
    log.debug(f"Logging will be sent directly to remote address {syslog_address}")
    syslog_server = urlparse(syslog_address)
except KeyError:
    pass
if syslog_server and len(syslog_server.netloc) > 0:
    protocol = None
    if syslog_server.scheme == "udp":
        protocol = socket.SOCK_DGRAM
    if syslog_server.hostname is not None and syslog_server.port is not None:
        log_handler = logging.handlers.SysLogHandler(
            address=(syslog_server.hostname, syslog_server.port), socktype=protocol
        )
    else:
        log.error("Invalid SYSLOG_ADDRESS: hostname or port is missing.")
elif os.path.exists("/dev/log"):
    log_handler = logging.handlers.SysLogHandler(address="/dev/log")
elif sys.stdout.isatty() or "SUPERVISOR_ENABLED" in os.environ:
    log.debug("Using console logging because there is a tty or under supervisord.")
    log_handler = logging.StreamHandler(stream=sys.stdout)

if log_handler:
    # define the log format
    formatter = logging.Formatter("%(name)s %(threadName)s [%(levelname)s] %(message)s")
    log_handler.setFormatter(formatter)
    log.addHandler(log_handler)

# use parent of this module's top-level __init__.py

app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
log.debug(f"Running from {app_path}")
if os.path.exists(WORK_DIR):
    log.debug(f"Using working directory {WORK_DIR}")
    # assert working directory for assumptions made (such as PyDrive)
    current_work_dir = os.getcwd()
    if current_work_dir != WORK_DIR:
        log.warning(f"Changing working directory from {current_work_dir} to {WORK_DIR}")
        os.chdir(WORK_DIR)

# locale settings
local_env = "LC_ALL"
locale_lc_all = os.getenv(local_env)
if locale_lc_all:
    log.info(f"Using locale LC_ALL, set to {locale_lc_all}.")
    try:
        locale.setlocale(locale.LC_ALL, locale_lc_all)
    except LocaleError as e:
        log.warning(
            f"Cannot apply locale setting {local_env} value {locale_lc_all}: {e!s}"
        )

app_config: ConfigParser = ConfigParser()
app_config.optionxform = str  # type: ignore
app_config_path = os.path.join(WORK_DIR, "app.conf")
if os.path.exists(app_config_path) and os.path.getsize(app_config_path) > 0:
    log.info(f"Loading application configuration from {app_config_path}")
    app_config.read([app_config_path])
    device_name = app_config.get("app", "device_name")
    DEVICE_NAME = device_name  # type: ignore
    device_name_base = device_name
    device_name_parts = device_name.split("-")
    if len(device_name_parts) > 2:
        # throw away any suffixes
        device_name_base = "-".join(device_name_parts[0:2])
    DEVICE_NAME_BASE = device_name_base  # type: ignore
else:
    log.debug(
        f'Setting DEVICE_NAME and DEVICE_NAME_BASE to "{APP_NAME}" due to missing configuration.'
    )
    DEVICE_NAME = APP_NAME
    DEVICE_NAME_BASE = APP_NAME

creds = Creds()
creds.validate_creds()
