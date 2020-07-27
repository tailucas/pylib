import logging
from pathlib import Path
from ..datetime import make_timestamp


log = logging.getLogger(Path(__file__).stem)


def post_count_metric(metric_name, count=1):
    try:
        APP_METRICS.put_metric_data(
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
                    'Unit': 'Count'
                },
            ]
        )
    except Exception:
        log.exception('Problem posting metric [{}={}]'.format(metric_name, count))
