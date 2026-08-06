---
paths:
  - "src/tailucas_pylib/**"
  - "tests/**"
  - "pyproject.toml"
---

# tailucas-pylib Coding Standards

Shared Python library consumed by all `tailucas` applications (base-app,
event-processor, inverter-monitor, net-tool, remote-monitor,
snapshot-processor). Changes here ripple into every downstream app, so
conservatism and backward compatibility are the default posture.

## 1. Package Layout

- Source lives in `src/tailucas_pylib/`; the build backend is `uv_build`.
- `__init__.py` is the application bootstrap: it configures the `log` logger
  (JSON formatter), loads `app.conf` from `WORK_DIR`, and resolves
  `APP_NAME` / `DEVICE_NAME` / `DEVICE_NAME_BASE`. It must stay import-safe
  with **no heavy dependencies** (stdlib + `python-json-logger` only).
- `creds.py` defines its own logger with `logging.getLogger(APP_NAME)` because
  it cannot import the package `__init__` (import cycle). Keep it that way.
- CLI entry points live under `tools/` and are exposed via `[project.scripts]`
  (`aws_configure`, `config_interpol`, `cred_tool`, `yaml_interpol`). Tools
  print to stdout/stderr; they do not use the `log` logger.

## 2. Optional Dependencies (Extras)

Heavy or situational dependencies are optional extras: `aws`, `creds`, `dto`,
`monitoring`, `mq`.

- NEVER add an unconditional top-level import of an optional dependency.
  Import lazily inside the function or class that needs it:

  ```python
  def _setup_cronitor():
      ...
      import cronitor  # optional 'monitoring' extra
  ```

- Degrade gracefully when an extra is missing (`try/except ImportError`).
- Downstream apps pin extras in their dependencies, e.g.
  `tailucas-pylib[creds,monitoring,mq]>=0.7.7`. Bump the package version when
  you change public behavior; keep the API additive where possible.

## 3. Threading & ZMQ Conventions

- Application threads subclass `AppThread` (registers with the thread nanny).
- Inter-thread transport is ZeroMQ inproc sockets (`URL_WORKER_*` constants in
  `zmq.py`); use `exception_handler` context manager for socket lifecycles and
  `try_close` / `Closable` for teardown.
- Shutdown flows through `threads.die()` (sets `shutting_down`, interrupts
  `interruptable_sleep`) and ends with `bye()`; never call `exit()` directly
  from app code.
- Blocking waits must use `interruptable_sleep.wait(...)` rather than
  `time.sleep(...)` so shutdown can interrupt them.

## 4. Error Handling Posture

- Use `ResourceWarning` to signal fatal dependency problems without flooding
  Sentry with regressions; `exception_handler` treats it specially.
- Capture to Sentry with `capture_exception` only for unexpected exceptions.
- Raise `AssertionError` for configuration/credential contract violations.

## 5. Style & Tooling

- Python >= 3.11; ruff line length 100; double quotes; `ruff format` applied.
- Lint gate: `uv run ruff check src/`, `uv run ruff format --check src/`,
  `uv run mypy src/tailucas_pylib/` (mypy is strict-configured but allows
  untyped defs; do not regress existing errors).
- Keep modules dependency-light; prefer stdlib.

## 6. Testing

- `make test` runs `uv run --group test pytest -v`; the full matrix is
  `make test-all` (hatch across all extra combinations).
- Verify at least: `uv run --group test pytest` (core) and
  `uv run --group test --extra aws --extra creds --extra dto --extra monitoring --extra mq pytest`
  (all extras) before considering a change done.
- Tests that assert on log output must follow the structured-logging testing
  rules in `logging.md` (assert static messages or `extra` fields, never
  interpolated text).
- Tests must not require network/1Password; mock or skip otherwise.

## 7. Documentation & Versioning

- Keep the README module inventory in sync when adding/removing modules.
- Bump `version` in `pyproject.toml` for any published change; downstream apps
  use `>=` bounds, so breaking changes require a minor bump and a note.
