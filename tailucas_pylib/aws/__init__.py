import builtins
import logging
import os


log = logging.getLogger(APP_NAME)  # type: ignore
boto3_session = None
aws_enabled = False

try:
    os.environ['AWS_ACCESS_KEY_ID']
    os.environ['AWS_SECRET_ACCESS_KEY']
    aws_enabled = True
except KeyError:
    if hasattr(builtins, 'creds_config') and hasattr(creds_config, 'aws_akid'):  # type: ignore
        log.debug('AWS environment variables unset. Setting in Python from credential provider.')
        os.environ['AWS_ACCESS_KEY_ID'] = creds_config.aws_akid  # type: ignore
        os.environ['AWS_SECRET_ACCESS_KEY'] = creds_config.aws_sak  # type: ignore
        aws_enabled = True

if aws_enabled:
    from boto3 import Session
    from botocore.session import Session as BotoCoreSession

    boto_session = BotoCoreSession()
    boto3_session = Session(
        aws_access_key_id=creds_config.aws_akid,  # type: ignore
        aws_secret_access_key=creds_config.aws_sak,  # type: ignore
        botocore_session=boto_session)

if hasattr(builtins, 'APP_CONFIG') and APP_CONFIG.has_section('botoflow'):  # type: ignore
    swf_region = APP_CONFIG.get('botoflow', 'region')  # type: ignore
    swf_domain = APP_CONFIG.get('botoflow', 'domain')  # type: ignore
