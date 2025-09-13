from configparser import ConfigParser
from logging import Logger, Handler
from os import getenv
from typing import List

APP_NAME = getenv("APP_NAME", "test")
WORK_DIR = getenv("WORK_DIR", "/tmp")
DEVICE_NAME = getenv("DEVICE_NAME")
DEVICE_NAME_BASE = None


class CredsProvider:
    def validate_creds(self):
        raise NotImplementedError()
    def get_creds(self, creds_path: str):
        raise NotImplementedError()
    def get_fields_from_sections(self, item_title: str, section_names: List[str]):
        raise NotImplementedError()


app_config: ConfigParser = None # type: ignore
log: Logger = None # type: ignore
log_handler: Handler = None # type: ignore

creds: CredsProvider = None # type: ignore
creds_use_connect_client: bool = True
creds_use_service_client: bool = True
