from os import path

import pytest


def _mock_service_client():
    """Build a mock 1Password Service Account client.

    Mirrors the live "Test" item used by the connect-server tests so that the
    service-account tests run without hitting the rate-limited 1Password API.
    """
    from unittest.mock import AsyncMock, MagicMock

    vault_id = "mockvault"
    item = MagicMock(
        id="testitem",
        title="Test",
        sections=[
            MagicMock(id="section1", title="testsection1"),
            MagicMock(id="section2", title="testsection2"),
            MagicMock(id="section3", title="testsection3"),
        ],
        fields=[
            MagicMock(title="username", value="testuser", section_id=None),
            MagicMock(title="password", value="testpass", section_id=None),
            MagicMock(title="password", value="testsection1pass", section_id="section1"),
            MagicMock(title="FOO", value="foovalue", section_id="section2"),
            MagicMock(title="BAR", value="barvalue", section_id="section3"),
        ],
    )
    secrets = {
        "Test/username": "testuser",
        "Test/password": "testpass",
        "Test/testsection1/password": "testsection1pass",
    }
    client = MagicMock(name="ServiceClient")
    client.vaults.list = AsyncMock(return_value=[MagicMock(id=vault_id, title="Mock Vault")])
    client.secrets.resolve = AsyncMock(
        side_effect=lambda reference: secrets[reference.split("/", 3)[-1]]
    )
    client.items.list = AsyncMock(return_value=[MagicMock(id=item.id, title=item.title)])
    client.items.get = AsyncMock(return_value=item)
    return client


@pytest.fixture(scope="session", params=["use_connect_client", "use_service_client"])
def setup_creds(request):
    from tailucas_pylib.creds import Creds

    if request.param == "use_service_client":
        pytest.importorskip("onepassword")
        from os import environ
        from unittest.mock import patch

        mock_client = _mock_service_client()

        async def authenticate(auth, integration_name, integration_version):
            return mock_client

        # token value is irrelevant with a mocked client, but must be set for
        # the client creation code path to run; patch.dict avoids leaking it
        with (
            patch.dict(environ, {"OP_SERVICE_ACCOUNT_TOKEN": "mock-token"}),
            patch("onepassword.Client.authenticate", authenticate),
        ):
            creds = Creds(use_connect_client=False, use_service_client=True)
    else:
        pytest.importorskip("onepasswordconnectsdk.client")
        creds = Creds(use_connect_client=True, use_service_client=False)
    creds.validate_creds()
    return creds


def test_get_secret_or_env_returns_env_when_no_secrets_dir(monkeypatch):
    import os

    from tailucas_pylib.creds import get_secret_or_env

    # simulate no container secrets directory present
    monkeypatch.setattr(os.path, "isfile", lambda p: False)
    var_name = "MY_TEST_VAR"
    var_value = "env_value_123"
    monkeypatch.setenv(var_name, var_value)

    result = get_secret_or_env(var_name)
    assert result == var_value


def test_get_secret_or_env_raises_when_env_missing_and_no_secrets_dir(monkeypatch):
    import os

    from tailucas_pylib.creds import get_secret_or_env

    # simulate no container secrets directory present
    monkeypatch.setattr(os.path, "isfile", lambda p: False)
    var_name = "UNSET_TEST_VAR"
    # ensure env var is not present
    monkeypatch.delenv(var_name, raising=False)
    assert get_secret_or_env(var_name) is None


def test_get_secret_or_env_reads_secret_file_and_validates_path(monkeypatch):
    import os

    from tailucas_pylib.creds import CONTAINER_SECRETS_PATH, get_secret_or_env

    # simulate container secrets directory present
    monkeypatch.setattr(os.path, "isfile", lambda p: True)

    var_name = "MySecretName"
    file_contents = "super_secret_value"
    expected_path = path.join(CONTAINER_SECRETS_PATH, var_name.lower())

    # fake open that asserts the path used matches expected_path and returns the contents
    from unittest.mock import mock_open, patch

    with patch("builtins.open", mock_open(read_data=file_contents)) as mock_file:
        # assert open(expected_path).read() == file_contents
        result = get_secret_or_env(var_name)
        mock_file.assert_called_with(expected_path)
        assert result == file_contents


def test_assertions():
    from tailucas_pylib.creds import Creds

    with pytest.raises(AssertionError, match="No 1Password client created"):
        creds = Creds(use_connect_client=False, use_service_client=False)
        creds.validate_creds(assertion_check=True)


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
    assert setup_creds.get_fields_from_sections("Test", ["testsection2", "testsection3"]) == {
        "FOO": "foovalue",
        "BAR": "barvalue",
    }
