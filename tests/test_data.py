import logging

import pytest


def test_make_payload_defaults():
    """Test make_payload with no arguments returns packed bytes."""
    from tailucas_pylib.data import make_payload

    result = make_payload()
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_make_payload_with_timestamp():
    """Test make_payload with an explicit timestamp string."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_make_payload_with_dict_data():
    """Test make_payload merges dict data into the payload."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00", data={"foo": "bar"}, pack=False)
    assert isinstance(result, dict)
    assert "timestamp" in result
    assert result["foo"] == "bar"
    assert "data" not in result


def test_make_payload_with_non_dict_data():
    """Test make_payload puts non-dict data under 'data' key."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00", data="raw_string", pack=False)
    assert isinstance(result, dict)
    assert "timestamp" in result
    assert result["data"] == "raw_string"


def test_make_payload_with_empty_data():
    """Test make_payload with empty data (should not add 'data' key)."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00", data="", pack=False)
    assert isinstance(result, dict)
    assert "timestamp" in result
    assert "data" not in result


def test_make_payload_pack_returns_bytes():
    """Test make_payload with pack=True returns bytes."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00", data={"x": 1}, pack=True)
    assert isinstance(result, bytes)


def test_make_payload_nopack_returns_dict():
    """Test make_payload with pack=False returns a dict."""
    from tailucas_pylib.data import make_payload

    result = make_payload(timestamp="1985-10-26T01:21:00-00:00", pack=False)
    assert isinstance(result, dict)
    assert "timestamp" in result


def test_make_payload_debug_logging(caplog):
    """Test make_payload logs JSON in debug mode."""
    import logging
    from tailucas_pylib.data import make_payload
    from tailucas_pylib import log

    # Set log level to DEBUG
    old_level = log.level
    log.setLevel(logging.DEBUG)
    try:
        with caplog.at_level(logging.DEBUG):
            make_payload(timestamp="1985-10-26T01:21:00-00:00", data={"test": "debug"}, pack=False)
        assert caplog.text != ""
    finally:
        log.setLevel(old_level)