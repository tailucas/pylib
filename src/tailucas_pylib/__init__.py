import locale
import logging
import logging.handlers
import os
import os.path
import socket
import sys
from configparser import ConfigParser
from locale import Error as LocaleError
from logging import Handler, Logger
from os import getenv
from pathlib import Path
from pythonjsonlogger.json import JsonFormatter
from urllib.parse import urlparse

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
_syslog_warning = None
_syslog_warning_extra = None
try:
    syslog_address = os.environ["SYSLOG_ADDRESS"]
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
        # only INFO to syslog
        log_handler.addFilter(lambda record: record.levelno >= logging.INFO)
    else:
        _syslog_warning = "Invalid SYSLOG_ADDRESS: hostname or port is missing."
        _syslog_warning_extra = {"syslog_address": syslog_address}

# define the log format
formatter = JsonFormatter(
    "{asctime}{name}{levelname}{message}{exc_info}{stack_info}",
    style="{",
    rename_fields={
        "asctime": "timestamp",
        "name": "logger",
        "levelname": "level",
    },
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    json_default=str,  # coerce bytes/datetime/POJOs safely instead of crashing
)

if log_handler:
    log_handler.setFormatter(formatter)
    log.addHandler(log_handler)
else:
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    log.addHandler(stdout_handler)

    # Route ERROR and above to stderr
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(lambda record: record.levelno >= logging.ERROR)
    log.addHandler(stderr_handler)


if syslog_server:
    log.debug(
        "Logging will be sent directly to remote address",
        extra={"syslog_address": syslog_address},
    )
elif _syslog_warning:
    log.debug(_syslog_warning, extra=_syslog_warning_extra)


# use parent of this module's top-level __init__.py

app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
log.debug("Running from application path", extra={"app_path": str(app_path)})
if os.path.exists(WORK_DIR):
    log.debug("Using working directory", extra={"work_dir": WORK_DIR})
    # assert working directory for assumptions made (such as PyDrive)
    current_work_dir = os.getcwd()
    if current_work_dir != WORK_DIR:
        log.debug(
            "Changing working directory",
            extra={"current_work_dir": current_work_dir, "work_dir": WORK_DIR},
        )
        os.chdir(WORK_DIR)

# locale settings
local_env = "LC_ALL"
locale_lc_all = os.getenv(local_env)
if locale_lc_all:
    log.debug("Using locale LC_ALL", extra={"lc_all": locale_lc_all})
    try:
        locale.setlocale(locale.LC_ALL, locale_lc_all)
    except LocaleError as e:
        log.debug(
            "Cannot apply locale setting",
            extra={"locale_env": local_env, "locale_value": locale_lc_all, "error": str(e)},
        )

app_config: ConfigParser = ConfigParser()
app_config.optionxform = str  # type: ignore
app_config_path = os.path.join(WORK_DIR, "app.conf")
if os.path.exists(app_config_path) and os.path.getsize(app_config_path) > 0:
    log.debug("Loading application configuration", extra={"app_config_path": app_config_path})
    app_config.read([app_config_path])
    if app_config.has_option("app", "device_name"):
        device_name = app_config.get("app", "device_name")
        DEVICE_NAME = device_name  # type: ignore
        device_name_base = device_name
        device_name_parts = device_name.split("-")
        if len(device_name_parts) > 2:
            # throw away any suffixes
            device_name_base = "-".join(device_name_parts[0:2])
        DEVICE_NAME_BASE = device_name_base  # type: ignore
if DEVICE_NAME is None:
    log.debug(
        "Setting DEVICE_NAME and DEVICE_NAME_BASE due to missing configuration",
        extra={"app_name": APP_NAME},
    )
    DEVICE_NAME = APP_NAME
    DEVICE_NAME_BASE = APP_NAME
