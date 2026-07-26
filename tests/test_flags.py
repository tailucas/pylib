from unittest.mock import MagicMock, patch

import pytest


def test_flag():
    pytest.importorskip("onepasswordconnectsdk.client")
    from tailucas_pylib.flags import is_flag_enabled
    assert is_flag_enabled("my-test-flag") is True


def test_is_flag_enabled_initializes_creds_once():
    """Test that _creds is initialized only on the first call."""
    # Reset the module-level _creds to None
    import tailucas_pylib.flags as flags_module

    flags_module._creds = None

    mock_creds_instance = MagicMock()
    mock_creds_instance.get_creds.return_value = "true"

    with patch(
        "tailucas_pylib.creds.Creds", return_value=mock_creds_instance
    ) as mock_creds_class:
        result = flags_module.is_flag_enabled("test-flag")

        # Verify Creds was constructed once
        mock_creds_class.assert_called_once()
        mock_creds_instance.validate_creds.assert_called_once()
        mock_creds_instance.get_creds.assert_called_once_with("flags/test-flag/value")
        assert result is True


def test_is_flag_enabled_false_value():
    """Test is_flag_enabled returns False for 'false' flag value."""
    import tailucas_pylib.flags as flags_module

    flags_module._creds = None

    mock_creds_instance = MagicMock()
    mock_creds_instance.get_creds.return_value = "false"

    with patch(
        "tailucas_pylib.creds.Creds", return_value=mock_creds_instance
    ):
        result = flags_module.is_flag_enabled("test-flag")
        assert result is False
