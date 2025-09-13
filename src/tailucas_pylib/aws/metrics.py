from ..datetime import make_timestamp
from .. import APP_NAME, DEVICE_NAME_BASE, log
from . import get_boto_session


METRIC_NAMESPACE = "automation"


_app_metrics = None


def post_count_metric(
    metric_name, count=1, unit="Count", dimensions=None, device_name=DEVICE_NAME_BASE
):  # type: ignore
    global _app_metrics
    if _app_metrics is None:
        _app_metrics = get_boto_session().client("cloudwatch")
    # define default dimensions
    metric_dimensions = [
        {
            "Name": "Application",
            "Value": APP_NAME,
        },
    ]
    if device_name:
        metric_dimensions.append({"Name": "Device", "Value": device_name})
    if isinstance(dimensions, dict):
        for k, v in list(dimensions.items()):
            metric_dimensions.append({"Name": k, "Value": v})
    try:
        _app_metrics.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": count,
                    "Dimensions": metric_dimensions,
                    "Timestamp": make_timestamp(),
                    "Unit": unit,
                },
            ],
        )
    except Exception as e:
        log.warning(f"Problem posting metric [{metric_name}={count}]: {e!r}")
