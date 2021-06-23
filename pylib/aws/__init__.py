import logging
import os

from boto3 import Session
from botocore.session import Session as BotoCoreSession

log = logging.getLogger(APP_NAME) # type: ignore

try:
    os.environ['AWS_ACCESS_KEY_ID']
    os.environ['AWS_SECRET_ACCESS_KEY']
except KeyError:
    log.debug('AWS environment variables unset. Setting in Python from credential provider.')
    os.environ['AWS_ACCESS_KEY_ID'] = creds_config.aws_akid # type: ignore
    os.environ['AWS_SECRET_ACCESS_KEY'] = creds_config.aws_sak # type: ignore

boto_session = BotoCoreSession()
boto3_session = Session(
    aws_access_key_id=creds_config.aws_akid, # type: ignore
    aws_secret_access_key=creds_config.aws_sak, # type: ignore
    botocore_session=boto_session)

swf_region = APP_CONFIG.get('botoflow', 'region') # type: ignore
swf_domain = APP_CONFIG.get('botoflow', 'domain') # type: ignore