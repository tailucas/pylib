import os

from ..config import log, app_config, creds, APP_NAME

boto3_session = None
aws_enabled = False

aws_region = None
aws_akid = None
aws_sak = None

try:
    aws_region = os.environ["AWS_REGION"]
    aws_akid = os.environ["AWS_ACCESS_KEY_ID"]
    aws_sak = os.environ["AWS_SECRET_ACCESS_KEY"]
    aws_enabled = True
except KeyError:
        log.debug(
            "AWS environment variables unset. Setting in Python from credential provider."
        )
        try:
            aws_region = app_config.get("aws", "region")
            aws_akid = creds.get_creds(f'AWS.{APP_NAME}/{aws_region}/akid') # type: ignore
            os.environ["AWS_ACCESS_KEY_ID"] = aws_akid
            aws_sak = creds.get_creds(f'AWS.{APP_NAME}/{aws_region}/sak' ) # type: ignore
            os.environ["AWS_SECRET_ACCESS_KEY"] = aws_sak
            aws_enabled = True
        except Exception as e:
            log.warning(f"Cannot enable AWS: {e!r}")

if aws_enabled:
    from boto3 import Session
    from botocore.session import Session as BotoCoreSession

    boto_session = BotoCoreSession()
    boto3_session = Session(
        aws_access_key_id=aws_akid,
        aws_secret_access_key=aws_sak,
        region_name=aws_region,
        botocore_session=boto_session
    )
