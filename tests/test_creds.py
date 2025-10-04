import pytest


@pytest.fixture(scope="session", params=["use_connect_client", "use_service_client"])
def setup_creds(request):
    from tailucas_pylib.creds import Creds

    creds = Creds(
        use_connect_client=(request.param == "use_connect_client"),
        use_service_client=(request.param == "use_service_client"),
    )
    creds.validate_creds()
    return creds


def test_get_secret_or_env_returns_env_when_no_secrets_dir(monkeypatch):
    import os
    from tailucas_pylib.creds import get_secret_or_env

    # simulate no container secrets directory present
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    var_name = "MY_TEST_VAR"
    var_value = "env_value_123"
    monkeypatch.setenv(var_name, var_value)

    result = get_secret_or_env(var_name)
    assert result == var_value


def test_get_secret_or_env_raises_when_env_missing_and_no_secrets_dir(monkeypatch):
    import os
    from tailucas_pylib.creds import get_secret_or_env

    # simulate no container secrets directory present
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    var_name = "UNSET_TEST_VAR"
    # ensure env var is not present
    monkeypatch.delenv(var_name, raising=False)

    with pytest.raises(
        AssertionError, match=f"Environment variable {var_name} is unset."
    ):
        get_secret_or_env(var_name)


def test_get_secret_or_env_reads_secret_file_and_validates_path(monkeypatch):
    import os
    from tailucas_pylib.creds import get_secret_or_env, CONTAINER_SECRETS_PATH

    # simulate container secrets directory present
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    var_name = "MySecretName"
    file_contents = "super_secret_value"
    expected_path = f"{CONTAINER_SECRETS_PATH}/{var_name.lower()}"

    # fake open that asserts the path used matches expected_path and returns the contents
    from unittest.mock import patch, mock_open

    with patch("builtins.open", mock_open(read_data=file_contents)) as mock_file:
        # assert open(expected_path).read() == file_contents
        result = get_secret_or_env(var_name)
        mock_file.assert_called_with(expected_path, "r")
        assert result == file_contents


def test_assertions():
    from tailucas_pylib.creds import Creds

    with pytest.raises(AssertionError, match="No 1Password client created"):
        creds = Creds(use_connect_client=False, use_service_client=False)
        creds.validate_creds()


def test_single_active_client(setup_creds):
    if setup_creds.connect_client:
        assert setup_creds.service_client is None
    if setup_creds.service_client:
        assert setup_creds.connect_client is None


@pytest.mark.parametrize("setup_creds", ["use_connect_client"], indirect=True)
def test_get_creds_connect_server(setup_creds):
    with pytest.raises(AssertionError, match="Ambiguous field specification"):
        setup_creds.get_creds("Test")
    with pytest.raises(
        AssertionError,
        match="Section nosection not found in item Test/nosection/noitem in vault",
    ):
        setup_creds.get_creds("Test/nosection/noitem")


def test_get_creds_service_account(setup_creds):
    assert setup_creds.get_creds("Test/username") == "testuser"
    assert setup_creds.get_creds("Test/password") == "testpass"
    assert setup_creds.get_creds("Test/testsection1/password") == "testsection1pass"


def test_get_fields_from_sections(setup_creds):
    assert setup_creds.get_fields_from_sections(
        "Test", ["testsection2", "testsection3"]
    ) == {"FOO": "foovalue", "BAR": "barvalue"}
