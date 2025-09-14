#!/usr/bin/env python

from botocore.credentials import Credentials
from configparser import ConfigParser
from os import getenv
from os.path import expanduser, exists, isdir, dirname

from . import err, outl as out
from .. import creds, APP_NAME
from ..aws import get_boto_session


def test_dir(path):
    expanded_path = expanduser(path)
    path_dir = dirname(expanded_path)
    if not exists(path_dir):
        err(f"Path {path_dir} does not exist for {path}.")
    elif not isdir(path_dir):
        err(f"Path {path_dir} is not a directory of {path}.")
    return expanded_path


AWS_CONFIG_FILE = test_dir(getenv("AWS_CONFIG_FILE", "~/.aws/config"))
AWS_SHARED_CREDENTIALS_FILE = test_dir(
    getenv("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials")
)


def main():
    aws_settings = creds.get_fields_from_sections(f"AWS.{APP_NAME}", ["config"])
    aws_config = ConfigParser()
    aws_config["default"] = {"region": aws_settings["AWS_REGION"], "output": "json"}
    out(f"Writing {AWS_CONFIG_FILE}...")
    with open(AWS_CONFIG_FILE, "w") as config_file:
        aws_config.write(config_file)
    boto_session = get_boto_session()
    boto_creds: Credentials = boto_session.get_credentials()
    aws_creds = ConfigParser()
    if boto_creds.access_key and boto_creds.secret_key and boto_creds.token:
        aws_creds["default"] = {
            "aws_access_key_id": boto_creds.access_key,
            "aws_secret_access_key": boto_creds.secret_key,
            "aws_session_token": boto_creds.token,
        }
    else:
        err("Boto session has no credentials for writing.", 2)
    out(f"Writing {AWS_SHARED_CREDENTIALS_FILE}...")
    with open(AWS_SHARED_CREDENTIALS_FILE, "w") as creds_file:
        aws_creds.write(creds_file)
    out("Done.")


if __name__ == "__main__":
    main()
