import boto3
import botocore

# set up application metrics
boto3_session = boto3.Session()
boto_session = botocore.session.Session()

from .metrics import app_metrics
from .swf import swf_region, swf_domain
