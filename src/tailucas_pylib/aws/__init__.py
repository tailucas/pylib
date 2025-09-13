from datetime import datetime, timezone

from botocore.exceptions import ClientError

from ..config import log, APP_NAME, creds

from boto3 import Session
from botocore.exceptions import ClientError


_region = None
_akid = None
_role_arn = None
_sts_client = None
_boto_session: Session = None # type: ignore
_boto_session_expiry: datetime = None # type: ignore


def get_boto_session() -> Session:
    global _region, _akid, _role_arn, _sts_client, _boto_session, _boto_session_expiry
    if _region is None:
        _region = creds.get_creds(f'AWS.{APP_NAME}/AWS_REGION')
    if _akid is None:
        _akid = creds.get_creds(f'AWS.{APP_NAME}/AWS_ACCESS_KEY_ID')
    if _role_arn is None:
        _role_arn = creds.get_creds(f'AWS.{APP_NAME}/AWS_ROLE_ARN')

    refresh_boto_session = False
    if _boto_session is None:
        refresh_boto_session = True
    elif _boto_session_expiry <= datetime.now(timezone.utc):
        refresh_boto_session = True

    role_session_name = f"{APP_NAME}-session"
    if not refresh_boto_session and _boto_session is not None:
        log.info(f'Using existing role session {role_session_name} with expiry of {_boto_session_expiry}...')
        return _boto_session

    assume_role_response = None
    try:
        if _sts_client is None:
            log.info(f'Creating AWS STS session using {_akid[:5]}...{_akid[-5:]} in region {_region}...')
            sak = creds.get_creds(f'AWS.{APP_NAME}/AWS_SECRET_ACCESS_KEY')
            temp_session = Session(
                aws_access_key_id=_akid,
                aws_secret_access_key=sak,
                region_name=_region
            )
            _sts_client = temp_session.client('sts')
        log.info(f"Assuming AWS role {_role_arn} in region {_region} for session {role_session_name}...")
        assume_role_response = _sts_client.assume_role(
            RoleArn=_role_arn,
            RoleSessionName=role_session_name
        )
    except ClientError as e:
        log.error(f"Failed to assume role {_role_arn}: {e}")
        raise

    if assume_role_response is None:
        raise AssertionError(f'No session token returned for STS call to assume role {_role_arn}')

    credentials = assume_role_response['Credentials']
    _boto_session_expiry = credentials['Expiration']
    log.info(f"Creating Boto session with expiration of {_boto_session_expiry}...")
    _boto_session = Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=_region
    )
    return _boto_session