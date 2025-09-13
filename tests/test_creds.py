import pytest

from tailucas_pylib.creds import Creds


@pytest.fixture(scope="session")
def setup_creds():
    creds = Creds()
    creds.validate_creds()
    return creds


def test_assertions(monkeypatch):
    monkeypatch.setenv("CREDS_USE_CONNECT_CLIENT", "false")
    monkeypatch.setenv("CREDS_USE_SERVICE_CLIENT", "false")
    with pytest.raises(Exception, match="No 1Password client created"):
        creds = Creds()
        creds.validate_creds()


def test_get_creds_connect_server(setup_creds, monkeypatch):
    monkeypatch.setenv("CREDS_USE_CONNECT_CLIENT", "true")
    monkeypatch.setenv("CREDS_USE_SERVICE_CLIENT", "false")
    with pytest.raises(AssertionError, match="Ambiguous field specification"):
        setup_creds.get_creds("Test")
    with pytest.raises(
        AssertionError,
        match="Section nosection not found in item Test/nosection/noitem in vault",
    ):
        setup_creds.get_creds("Test/nosection/noitem")
    assert setup_creds.get_creds("Test/username") == "testuser"
    assert setup_creds.get_creds("Test/password") == "testpass"
    assert setup_creds.get_creds("Test/testsection1/password") == "testsection1pass"


def test_get_creds_service_account(setup_creds, monkeypatch):
    monkeypatch.setenv("CREDS_USE_CONNECT_CLIENT", "false")
    monkeypatch.setenv("CREDS_USE_SERVICE_CLIENT", "true")
    assert setup_creds.get_creds("Test/username") == "testuser"
    assert setup_creds.get_creds("Test/password") == "testpass"
    assert setup_creds.get_creds("Test/testsection1/password") == "testsection1pass"


def test_get_fields_from_sections_connect_server(setup_creds, monkeypatch):
    monkeypatch.setenv("CREDS_USE_CONNECT_CLIENT", "true")
    monkeypatch.setenv("CREDS_USE_SERVICE_CLIENT", "false")
    assert setup_creds.get_fields_from_sections(
        "Test", ["testsection2", "testsection3"]
    ) == {"FOO": "foovalue", "BAR": "barvalue"}


def test_get_fields_from_sections_service_account(setup_creds, monkeypatch):
    monkeypatch.setenv("CREDS_USE_CONNECT_CLIENT", "false")
    monkeypatch.setenv("CREDS_USE_SERVICE_CLIENT", "true")
    assert setup_creds.get_fields_from_sections(
        "Test", ["testsection2", "testsection3"]
    ) == {"FOO": "foovalue", "BAR": "barvalue"}
