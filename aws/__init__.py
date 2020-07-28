import boto3
import botocore

# set up application metrics
boto3_session = boto3.Session()
boto_session = botocore.session.Session()

swf_region = APP_CONFIG.get('botoflow', 'region')
swf_domain = APP_CONFIG.get('botoflow', 'domain')
