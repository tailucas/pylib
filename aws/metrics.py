import logging
from . import boto3_session
from ..datetime import make_timestamp


log = logging.getLogger(APP_NAME)


app_metrics = boto3_session.client('cloudwatch')


def post_count_metric(metric_name, count=1, unit='Count'):
    global app_metrics
    try:
        app_metrics.put_metric_data(
            Namespace='automation',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': count,
                    'Dimensions': [
                        {
                            'Name': 'Application',
                            'Value': APP_NAME
                        },
                        {
                            'Name': 'Device',
                            'Value': DEVICE_NAME
                        },
                    ],
                    'Timestamp': make_timestamp(),
                    'Unit': unit
                },
            ]
        )
    except Exception as e:
        log.warning('Problem posting metric [{}={}]: {}'.format(metric_name, count, repr(e)))
