import logging
import os

from boto3 import Session
from botocore.session import Session as BotoCoreSession

log = logging.getLogger(APP_NAME) # pylint: disable=undefined-variable

try:
    os.environ['AWS_ACCESS_KEY_ID']
    os.environ['AWS_SECRET_ACCESS_KEY']
except KeyError:
    log.debug('AWS environment variables unset. Setting in Python from credential provider.')
    os.environ['AWS_ACCESS_KEY_ID'] = creds_config.aws_akid # pylint: disable=undefined-variable
    os.environ['AWS_SECRET_ACCESS_KEY'] = creds_config.aws_sak # pylint: disable=undefined-variable

boto_session = BotoCoreSession()
boto3_session = Session(
    aws_access_key_id=creds_config.aws_akid, # pylint: disable=undefined-variable
    aws_secret_access_key=creds_config.aws_sak, # pylint: disable=undefined-variable
    botocore_session=boto_session)

swf_region = APP_CONFIG.get('botoflow', 'region') # pylint: disable=undefined-variable
swf_domain = APP_CONFIG.get('botoflow', 'domain') # pylint: disable=undefined-variable