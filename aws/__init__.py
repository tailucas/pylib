from boto3 import Session
from botocore.session import Session as BotoCoreSession

boto_session = BotoCoreSession()
boto3_session = Session(
    aws_access_key_id=creds.aws_akid, # pylint: disable=undefined-variable
    aws_secret_access_key=creds.aws_sak, # pylint: disable=undefined-variable
    botocore_session=boto_session)
