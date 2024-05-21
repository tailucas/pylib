import builtins
import logging
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from zmq.error import ContextTerminated, ZMQError

builtins.PYTEST = True
app_name = "testapp"
builtins.APP_NAME = app_name

from pylib.zmq import Closable


def validate(
    exception_name, caplog, log_exception=True, sentry_mock=None, sleep_mock=None
):
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
    if log_exception:
        assert logged_exception
    if sentry_mock:
        sentry_mock.assert_called
    if sleep_mock:
        sleep_mock.assert_called
    caplog.clear()


def test_handler(caplog, mocker: MockerFixture):
    caplog.set_level(logging.DEBUG, logger=app_name)
    sentry = mocker.patch("sentry_sdk.capture_exception")
    sleeper = mocker.patch("time.sleep")

    from pylib.handler import exception_handler

    # no exception
    with exception_handler():
        pass
    assert len(caplog.text) == 0
    sentry.assert_not_called

    exception_method = Mock()

    # ZMQ-specific
    exception_method.side_effect = ContextTerminated()
    with pytest.raises(ContextTerminated):
        with exception_handler(closable=Closable(name="foo")):
            exception_method()
    validate(
        exception_name=exception_method.side_effect.__class__.__name__,
        caplog=caplog,
        log_exception=False,
    )

    # ZMQ-generic
    exception_method.side_effect = ZMQError()
    with pytest.raises(ZMQError):
        with exception_handler():
            exception_method()
    validate(
        exception_name=exception_method.side_effect.__class__.__name__, caplog=caplog
    )

    # generic exception
    exception_method.side_effect = ValueError()
    with pytest.raises(ValueError):
        with exception_handler():
            exception_method()
    validate(
        exception_name=exception_method.side_effect.__class__.__name__,
        caplog=caplog,
        sentry_mock=sentry,
    )
