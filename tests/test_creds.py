import pytest

from tailucas_pylib.creds import Creds
import tailucas_pylib.creds as creds_mod


@pytest.fixture(scope="session")
def setup_creds():
    creds = Creds()
    creds.validate_creds()
    return creds

def test_assertions(setup_creds, monkeypatch):
    monkeypatch.setattr(creds_mod, "creds_use_connect_client", False, raising=False)
    monkeypatch.setattr(creds_mod, "creds_use_service_client", False, raising=False)
    with pytest.raises(AssertionError):
        setup_creds.get_creds("Test")

def test_get_creds_connect_server(setup_creds, monkeypatch):
    monkeypatch.setattr(creds_mod, "creds_use_connect_client", True, raising=False)
    monkeypatch.setattr(creds_mod, "creds_use_service_client", False, raising=False)
    with pytest.raises(AssertionError):
        setup_creds.get_creds("Test")
    with pytest.raises(AssertionError):
        setup_creds.get_creds("Test/nosection/noitem")
    assert setup_creds.get_creds("Test/username") == "testuser"
    assert setup_creds.get_creds("Test/password") == "testpass"
    assert setup_creds.get_creds("Test/testsection1/password") == "testsection1pass"

def test_get_creds_service_account(setup_creds, monkeypatch):
    monkeypatch.setattr(creds_mod, "creds_use_connect_client", False, raising=False)
    monkeypatch.setattr(creds_mod, "creds_use_service_client", True, raising=False)
    assert setup_creds.get_creds("Test/username") == "testuser"
    assert setup_creds.get_creds("Test/password") == "testpass"
    assert setup_creds.get_creds("Test/testsection1/password") == "testsection1pass"

def test_get_fields_from_sections_connect_server(setup_creds, monkeypatch):
    monkeypatch.setattr(creds_mod, "creds_use_connect_client", True, raising=False)
    monkeypatch.setattr(creds_mod, "creds_use_service_client", False, raising=False)
    assert setup_creds.get_fields_from_sections("Test", ["testsection2", "testsection3"]) == {
        "FOO": "foovalue",
        "BAR": "barvalue"
        }

def test_get_fields_from_sections_service_account(setup_creds, monkeypatch):
    monkeypatch.setattr(creds_mod, "creds_use_connect_client", False, raising=False)
    monkeypatch.setattr(creds_mod, "creds_use_service_client", True, raising=False)
    assert setup_creds.get_fields_from_sections("Test", ["testsection2", "testsection3"]) == {
        "FOO": "foovalue",
        "BAR": "barvalue"
        }