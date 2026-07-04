import io
import os

import pytest


# ==============================================================
# tools/__init__.py: err(), out(), outl()
# ==============================================================


def test_err_writes_to_stderr_and_exits(capsys):
    """Test err() writes message to stderr and exits with given code."""
    from tailucas_pylib.tools import err

    with pytest.raises(SystemExit) as exc_info:
        err("something bad", code=2)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "something bad" in captured.err


def test_err_default_exit_code(capsys):
    """Test err() defaults to exit code 1."""
    from tailucas_pylib.tools import err

    with pytest.raises(SystemExit) as exc_info:
        err("default code")
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "default code" in captured.err


def test_out_writes_to_stdout_no_exit(capsys):
    """Test out() writes to stdout and does NOT exit when code is None."""
    from tailucas_pylib.tools import out

    out("hello world")
    captured = capsys.readouterr()
    assert captured.out == "hello world"


def test_out_exits_with_nonzero_code(capsys):
    """Test out() writes to stdout and exits with non-zero code."""
    from tailucas_pylib.tools import out

    with pytest.raises(SystemExit) as exc_info:
        out("done", code=2)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == "done"


def test_out_code_zero_does_not_exit(capsys):
    """Test out() does NOT exit when code=0 (falsy)."""
    from tailucas_pylib.tools import out

    # Should not raise SystemExit
    out("done", code=0)
    captured = capsys.readouterr()
    assert captured.out == "done"


def test_outl_appends_newline(capsys):
    """Test outl() appends an OS line separator and delegates to out()."""
    from tailucas_pylib.tools import outl

    outl("line text")
    captured = capsys.readouterr()
    assert captured.out.rstrip("\n\r") == "line text"
    assert captured.out.endswith(os.linesep)


# ==============================================================
# tools/yaml_interpol.py: update_section()
# ==============================================================


def test_update_section_shallow():
    """Test update_section replaces a top-level key."""
    from tailucas_pylib.tools.yaml_interpol import update_section

    yaml_dict = {"foo": "old", "bar": "keep"}
    update_section(yaml_dict, ["foo"], "new_value")
    assert yaml_dict == {"foo": "new_value", "bar": "keep"}


def test_update_section_nested():
    """Test update_section navigates nested keys to replace a leaf."""
    from tailucas_pylib.tools.yaml_interpol import update_section

    yaml_dict = {
        "services": {
            "app": {
                "image": "old-image:1.0",
                "ports": ["8080:8080"],
            }
        }
    }
    update_section(yaml_dict, ["services", "app", "image"], "new-image:2.0")
    assert yaml_dict["services"]["app"]["image"] == "new-image:2.0"
    assert yaml_dict["services"]["app"]["ports"] == ["8080:8080"]


def test_update_section_multiple_calls():
    """Test update_section can be called multiple times on the same dict."""
    from tailucas_pylib.tools.yaml_interpol import update_section

    yaml_dict = {"a": {"b": {"c": 1, "d": 2}}}
    update_section(yaml_dict, ["a", "b", "c"], 99)
    update_section(yaml_dict, ["a", "b", "d"], 100)
    assert yaml_dict == {"a": {"b": {"c": 99, "d": 100}}}


def test_update_section_deeply_nested():
    """Test update_section with a deeply nested path."""
    from tailucas_pylib.tools.yaml_interpol import update_section

    yaml_dict = {"l1": {"l2": {"l3": {"l4": {"key": "old"}}}}}
    update_section(yaml_dict, ["l1", "l2", "l3", "l4", "key"], "new")
    assert yaml_dict["l1"]["l2"]["l3"]["l4"]["key"] == "new"


# ==============================================================
# tools/config_interpol.py: load_config()
# ==============================================================


def test_load_config_simple_key_value():
    """Test load_config parses a simple key=value pair into FAKE_SECTION."""
    from tailucas_pylib.tools.config_interpol import load_config, FAKE_SECTION

    fp = io.StringIO("my_key=my_value\n")
    cfg = load_config(fp)
    assert cfg.has_section(FAKE_SECTION)
    assert cfg.get(FAKE_SECTION, "my_key") == "my_value"


def test_load_config_with_sections():
    """Test load_config parses INI-style sections."""
    from tailucas_pylib.tools.config_interpol import load_config, FAKE_SECTION

    content = (
        "default_key=default_value\n"
        "[app]\n"
        "name=myapp\n"
        "port=8080\n"
    )
    fp = io.StringIO(content)
    cfg = load_config(fp)
    assert cfg.get(FAKE_SECTION, "default_key") == "default_value"
    assert cfg.has_section("app")
    assert cfg.get("app", "name") == "myapp"
    assert cfg.get("app", "port") == "8080"


def test_load_config_with_env_interpolation(monkeypatch):
    """Test load_config parses values; interpolation uses BasicInterpolation %(name)s syntax."""
    from tailucas_pylib.tools.config_interpol import load_config, FAKE_SECTION

    monkeypatch.setenv("MY_HOST", "localhost")
    monkeypatch.setenv("MY_PORT", "5432")

    # BasicInterpolation uses %(name)s, not ${name}
    fp = io.StringIO("host=%(MY_HOST)s\nport=%(MY_PORT)s\n")
    cfg = load_config(fp)
    assert cfg.get(FAKE_SECTION, "host", vars=os.environ) == "localhost"
    assert cfg.get(FAKE_SECTION, "port", vars=os.environ) == "5432"


def test_load_config_empty_file():
    """Test load_config handles an empty file-like object."""
    from tailucas_pylib.tools.config_interpol import load_config, FAKE_SECTION

    fp = io.StringIO("")
    cfg = load_config(fp)
    assert cfg.has_section(FAKE_SECTION)


# ==============================================================
# tools/cred_tool.py: main() argument parsing
# ==============================================================


def test_cred_tool_main_reads_cred_path_from_stdin(monkeypatch, capsys):
    """Test main() with no args reads cred path from stdin and outputs cred."""
    from unittest.mock import MagicMock, patch

    mock_creds_instance = MagicMock()
    mock_creds_instance.get_creds.return_value = "secret-value"

    with patch(
        "tailucas_pylib.tools.cred_tool.Creds", return_value=mock_creds_instance
    ):
        from tailucas_pylib.tools.cred_tool import main

        monkeypatch.setattr("sys.argv", ["cred_tool"])
        monkeypatch.setattr("sys.stdin", io.StringIO("Test/username\n"))

        # out(code=0) does NOT raise SystemExit (0 is falsy)
        main()

        mock_creds_instance.validate_creds.assert_called_once()
        mock_creds_instance.get_creds.assert_called_once_with("Test/username")
        captured = capsys.readouterr()
        assert "secret-value" in captured.out


def test_cred_tool_main_errors_on_empty_stdin(monkeypatch, capsys):
    """Test main() calls err() when stdin provides an empty cred path."""
    from unittest.mock import MagicMock, patch

    mock_creds_instance = MagicMock()

    with patch(
        "tailucas_pylib.tools.cred_tool.Creds", return_value=mock_creds_instance
    ):
        from tailucas_pylib.tools.cred_tool import main

        monkeypatch.setattr("sys.argv", ["cred_tool"])
        monkeypatch.setattr("sys.stdin", io.StringIO("\n"))

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No credential path" in captured.err


def test_cred_tool_main_uses_item_and_sections(monkeypatch, capsys):
    """Test main() with >=3 args calls get_fields_from_sections and outputs JSON."""
    from unittest.mock import MagicMock, patch

    mock_creds_instance = MagicMock()
    mock_creds_instance.get_fields_from_sections.return_value = {"FOO": "bar"}

    with patch(
        "tailucas_pylib.tools.cred_tool.Creds", return_value=mock_creds_instance
    ):
        from tailucas_pylib.tools.cred_tool import main

        monkeypatch.setattr("sys.argv", ["cred_tool", "MyItem", "section1", "section2"])

        # out() without code does NOT raise SystemExit
        main()

        mock_creds_instance.validate_creds.assert_called_once()
        mock_creds_instance.get_fields_from_sections.assert_called_once_with(
            "MyItem", ["section1", "section2"]
        )
        captured = capsys.readouterr()
        assert '"FOO"' in captured.out


def test_cred_tool_main_errors_on_two_args(monkeypatch, capsys):
    """Test main() with exactly 2 args calls err()."""
    from unittest.mock import MagicMock, patch

    mock_creds_instance = MagicMock()

    with patch(
        "tailucas_pylib.tools.cred_tool.Creds", return_value=mock_creds_instance
    ):
        from tailucas_pylib.tools.cred_tool import main

        monkeypatch.setattr("sys.argv", ["cred_tool", "only_one_arg"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unexpected arguments" in captured.err