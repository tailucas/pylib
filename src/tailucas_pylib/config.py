from configparser import ConfigParser
from logging import Logger, Handler
from os import getenv

APP_NAME = getenv("APP_NAME", "test")
WORK_DIR = getenv("WORK_DIR", "/tmp")
DEVICE_NAME = getenv("DEVICE_NAME")
DEVICE_NAME_BASE = None

app_config: ConfigParser = None # type: ignore
log: Logger = None # type: ignore
log_handler: Handler = None # type: ignore

creds = None # type: ignore
creds_use_connect_client=True
creds_use_service_client=True
