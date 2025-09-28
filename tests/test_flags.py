from tailucas_pylib.flags import is_flag_enabled


def test_flag():
    assert is_flag_enabled("my-test-flag") is True
