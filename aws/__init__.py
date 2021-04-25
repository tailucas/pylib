from boto3 import Session
from botocore.session import Session as BotoCoreSession

boto_session = BotoCoreSession()
boto3_session = Session(
    aws_access_key_id=creds_config.aws_akid, # pylint: disable=undefined-variable
    aws_secret_access_key=creds_config.aws_sak, # pylint: disable=undefined-variable
    botocore_session=boto_session)

swf_region = APP_CONFIG.get('botoflow', 'region') # pylint: disable=undefined-variable
swf_domain = APP_CONFIG.get('botoflow', 'domain') # pylint: disable=undefined-variable