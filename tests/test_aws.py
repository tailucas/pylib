import pytest

pytest.importorskip("boto3", reason="requires the 'aws' extra")


def test_session_caching(caplog):
    from tailucas_pylib.aws import get_boto_session
    caplog.set_level("DEBUG")
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
    from tailucas_pylib.aws.metrics import post_count_metric
    caplog.set_level("DEBUG")
    post_count_metric(
        "TestMetric",
        count=1,
        dimensions={"TestDimension": "TestValue"},
        device_name="TestDevice",
    )
    assert "Problem posting metric" not in caplog.text
