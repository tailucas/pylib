import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock, Mock, patch

import builtins
builtins.PYTEST = True
import logging

app_name = 'testapp'
builtins.APP_NAME = app_name


@pytest.mark.skip(reason='Figure out import order.')
def test_no_exception(caplog, mocker: MockerFixture):
    caplog.set_level(logging.INFO, logger=app_name)
    from pylib.handler import exception_handler
    with exception_handler():
        pass
    assert len(caplog.text) == 0

def test_generic_exception(caplog, mocker: MockerFixture):
    caplog.set_level(logging.DEBUG, logger=app_name)
    sentry = mocker.patch('sentry_sdk.capture_exception')
    sleeper = mocker.patch('time.sleep')
    exception_name = 'foo'
    exception_method = Mock()
    exception_method.side_effect = ValueError(exception_name)

    from pylib.handler import exception_handler
    with exception_handler():
        exception_method()

    logged_debug = False
    logged_exception = False
    for record in caplog.records:
        if record.levelname == "DEBUG":
            logged_debug = True
        if record.levelname == "ERROR":
            logged_exception = True
    assert len(caplog.text) != 0
    assert exception_name in caplog.text
    assert logged_debug
    assert logged_exception
    assert sentry.called
    assert sleeper.called
