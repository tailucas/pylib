import pytest

from tailucas_pylib.aws import get_boto_session
from tailucas_pylib.aws.metrics import post_count_metric


def test_session_caching(caplog):
    caplog.set_level("INFO")
    boto_session = get_boto_session()
    assert boto_session is not None
    assert "Creating Boto session with expiration" in caplog.text
    boto_session = get_boto_session()
    assert boto_session is not None
    assert "Using existing role session" in caplog.text


def test_post_metric(caplog):
    caplog.set_level("WARNING")
    post_count_metric("TestMetric", count=1, dimensions={"TestDimension": "TestValue"}, device_name="TestDevice")
    assert "Problem posting metric" not in caplog.text
