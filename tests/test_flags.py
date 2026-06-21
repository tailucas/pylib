import pytest


def test_flag():
    pytest.importorskip("onepasswordconnectsdk.client")
    from tailucas_pylib.flags import is_flag_enabled
    assert is_flag_enabled("my-test-flag") is True
