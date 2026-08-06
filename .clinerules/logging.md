---
paths:
  - "src/tailucas_pylib/**"
  - "tests/**"
  - "pyproject.toml"
---

# Structured Logging Standard (tailucas-pylib)

This library is the source of truth for logging across all derived applications.
It configures the application logger once, at import time, in
`src/tailucas_pylib/__init__.py` and exposes it as `log`.

## The Core Rule

Logging is **structured**: a static, human-readable event message plus
machine-readable fields passed via the `extra` keyword argument.

```python
log.info("Credential vault on 1Password server", extra={
    "server": self.op_connect_host,
    "vault_name": vault.name,
    "vault_id": vault.id,
    "credential_count": vault.items,
})
```

Interpolated logging is **prohibited** in this package. Never:

```python
# WRONG: f-string interpolation
log.debug(f"Reading secret for {var_name} from {secret_file}.")
# WRONG: lazy %-style arguments
log.debug("Signal %s received.", signum)
# WRONG: str.format()
log.info("Shutting down {}...".format(component))
# WRONG: concatenation
log.info("Problem posting metric [" + metric_name + "]")
# WRONG: dynamic message content (data as the message)
log.debug(json.dumps(payload))
```

## Why

The `log` logger is formatted with `pythonjsonlogger.json.JsonFormatter`.
Every key in `extra` becomes a top-level JSON field in the emitted log record,
which makes logs queryable and alertable in downstream log aggregation.
Interpolated messages bury data inside free text where it cannot be indexed.

## Rules

1. **Static message, data in `extra`.** The message names the event
   ("Signal received", not "Signal 15 received"). Data goes into `extra`
   as a `dict` with `snake_case` keys.
2. **Logger acquisition.** Library modules must use the package logger:
   `from . import log` (or `from .. import log` in subpackages). Do not call
   `logging.getLogger()` directly except in `__init__.py` and `creds.py`
   (which must not import the package `__init__` to avoid a cycle).
3. **Never log secrets.** No tokens, passwords, DSNs, or access keys. Use a
   masked hint (e.g. `f"{akid[:5]}...{akid[-5:]}"`) or a boolean
   (`"token_set": bool(token)`).
4. **Exceptions.** Use `log.exception("Static message", extra={...})` inside
   `except` blocks, or `exc_info=True` to attach a traceback to any level.
   Put the exception text into `extra` (`"error": str(e)`) only when the
   traceback is not attached.
5. **Serializable values.** Prefer JSON-native values (`str`, `int`, `float`,
   `bool`, `list`, `dict`). The formatter coerces other types with `str`
   (`json_default=str`), but explicit conversion (`str(timestamp)`,
   `repr(socket)`) is preferred for readability.
6. **Do not configure handlers outside `__init__.py`.** This module owns the
   handler/formatter setup (stdout/stderr split, or `SysLogHandler` when
   `SYSLOG_ADDRESS` is set). Applications only adjust `log.setLevel(...)`.
7. **Level guidance.**
   - `DEBUG`: internal state transitions, per-message tracing.
   - `INFO`: lifecycle events (startup, shutdown, connections), business events.
   - `WARNING`: recoverable problems, retries, degraded behavior.
   - `ERROR`: operation failures that need attention.
   - `CRITICAL`: reserved; prefer `ERROR` + `die(exception=...)`.
8. **Hot paths.** Guard expensive `extra` construction with
   `if log.level == logging.DEBUG:` and sample chatty logs (see the
   `randint` sampling pattern in derived apps).
9. **Reusable message + fields.** When the same event is logged at different
   levels, keep the static message and field dict in variables:

   ```python
   log_msg = "Message has no 'timestamp' so it can't be filtered if stale; using current time"
   log_fields = {"event_origin": event_origin, "timestamp_used": make_iso_timestamp(timestamp)}
   if stale:
       log.warning(log_msg, extra=log_fields)
   else:
       log.debug(log_msg, extra=log_fields)
   ```

## Testing Log Output

Tests must not assert on interpolated message content. Assert on the static
message (via `caplog.text`) or, preferably, on structured fields (via
`caplog.records` attributes):

```python
with caplog.at_level("DEBUG"):
    exec_cmd_log(["echo", "log-test"])
assert any(
    getattr(record, "exit_code", None) == 0
    and "log-test" in getattr(record, "stdout", "")
    for record in caplog.records
)
```

## Environment Contract

- `APP_NAME` names the logger; `LOG_LEVEL` (optional) sets the level.
- `SYSLOG_ADDRESS` (`udp://host:port`) routes logs to syslog at INFO+; without
  it, logs go to stdout (< ERROR) and stderr (>= ERROR), both JSON-formatted.
