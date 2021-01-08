import logging
from . import boto3_session
from ..datetime import make_timestamp


log = logging.getLogger(APP_NAME)


app_metrics = boto3_session.client('cloudwatch')


def post_count_metric(metric_name, count=1, unit='Count', dimensions=None):
    global app_metrics
    # post using device name base
    device_name_base = DEVICE_NAME
    device_name_parts = device_name_base.split('-')
    if len(device_name_parts) > 2:
        # throw away any suffixes
        device_name_base = '-'.join(device_name_parts[0:2])
    # define default dimensions
    metric_dimensions = [
        {
            'Name': 'Application',
            'Value': APP_NAME
        },
        {
            'Name': 'Device',
            'Value': device_name_base
        },
    ]
    if isinstance(dimensions, dict):
        for k, v in list(dimensions.items()):
            metric_dimensions.append({
                'Name': k,
                'Value': v
            })
    try:
        app_metrics.put_metric_data(
            Namespace='automation',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': count,
                    'Dimensions': metric_dimensions,
                    'Timestamp': make_timestamp(),
                    'Unit': unit
                },
            ]
        )
    except Exception as e:
        log.warning('Problem posting metric [{}={}]: {}'.format(metric_name, count, repr(e)))
