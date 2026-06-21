import pytest


def test_session_caching(caplog):
    pytest.importorskip("boto3")
    from tailucas_pylib.aws import get_boto_session
    caplog.set_level("INFO")
    boto_session = get_boto_session()
    assert boto_session is not None
    expected_strings = [
        "Creating Boto session with expiration",
        "Using existing role session test-session with expiry of",
    ]
    assert any(s in caplog.text for s in expected_strings)
    boto_session = get_boto_session()
    assert boto_session is not None
    assert "Using existing role session" in caplog.text


def test_post_metric(caplog):
    pytest.importorskip("boto3")
    from tailucas_pylib.aws.metrics import post_count_metric
    caplog.set_level("WARNING")
    post_count_metric(
        "TestMetric",
        count=1,
        dimensions={"TestDimension": "TestValue"},
        device_name="TestDevice",
    )
    assert "Problem posting metric" not in caplog.text
