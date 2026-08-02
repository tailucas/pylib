from unittest.mock import patch

import pytest


def test_exec_cmd_success():
    """Test exec_cmd returns stdout, stderr, and return code for a successful command."""
    from tailucas_pylib.process import exec_cmd

    out, err, rc = exec_cmd(["echo", "hello"])
    assert rc == 0
    assert b"hello" in out


def test_exec_cmd_failure():
    """Test exec_cmd returns non-zero return code for a failing command."""
    from tailucas_pylib.process import exec_cmd

    out, err, rc = exec_cmd(["ls", "/nonexistent/path/should/fail"])
    assert rc != 0


def test_exec_cmd_log(caplog):
    """Test exec_cmd_log calls exec_cmd and logs output."""
    from tailucas_pylib.process import exec_cmd_log

    with caplog.at_level("DEBUG"):
        exec_cmd_log(["echo", "log-test"])
    assert "log-test" in caplog.text