import logging
from . import boto3_session
from ..datetime import make_timestamp


log = logging.getLogger(APP_NAME)  # type: ignore

app_metrics = None
if boto3_session is not None:
    app_metrics = boto3_session.client('cloudwatch')
else:
    log.warning('AWS boto3_session is not set. CloudWatch metrics will be unavailable.')


def post_count_metric(metric_name, count=1, unit='Count', dimensions=None, device_name=DEVICE_NAME_BASE):  # type: ignore
    global app_metrics
    if app_metrics is None:
        return
    # define default dimensions
    metric_dimensions = [
        {
            'Name': 'Application',
            'Value': APP_NAME  # type: ignore
        },
        {
            'Name': 'Device',
            'Value': device_name
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
        log.warning(f'Problem posting metric [{metric_name}={count}]: {e!r}')
