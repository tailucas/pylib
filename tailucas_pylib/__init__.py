import builtins
import logging.handlers
import os
import os.path
import socket
import sys

from urllib.parse import urlparse

if hasattr(builtins, "PYTEST"):
    pass
else:
    from app import APP_NAME, WORK_DIR

    builtins.APP_NAME = APP_NAME  # type: ignore
    builtins.APP_PATH = WORK_DIR  # type: ignore

    log = logging.getLogger(APP_NAME)

    # do not propagate to console logging
    log.propagate = False
    # DEBUG logging until startup complete
    log.setLevel(logging.DEBUG)
    log_handler = None

    syslog_server = None
    try:
        syslog_address = os.environ["SYSLOG_ADDRESS"]
        log.warning(f'Logging will be sent directly to remote address {syslog_address}')
        syslog_server = urlparse(syslog_address)
    except KeyError:
        pass
    if syslog_server and len(syslog_server.netloc) > 0:
        protocol = None
        if syslog_server.scheme == 'udp':
            protocol = socket.SOCK_DGRAM
        log_handler = logging.handlers.SysLogHandler(address=(syslog_server.hostname, syslog_server.port), socktype=protocol)
    elif os.path.exists("/dev/log"):
        log_handler = logging.handlers.SysLogHandler(address="/dev/log")
    elif sys.stdout.isatty() or "SUPERVISOR_ENABLED" in os.environ:
        log.warning("Using console logging because there is a tty or under supervisord.")
        log_handler = logging.StreamHandler(stream=sys.stdout)
    if log_handler:
        # define the log format
        formatter = logging.Formatter("%(name)s %(threadName)s [%(levelname)s] %(message)s")
        log_handler.setFormatter(formatter)
        log.addHandler(log_handler)

    builtins.log = log  # type: ignore
    builtins.log_handler = log_handler  # type: ignore

    # use parent of this module's top-level __init__.py
    from pathlib import Path

    app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
    log.debug(f"Running from {app_path}, using working directory {WORK_DIR}")
    # assert working directory for assumptions made (such as PyDrive)
    current_work_dir = os.getcwd()
    if current_work_dir != WORK_DIR:
        log.warning(f"Changing working directory from {current_work_dir} to {WORK_DIR}")
        os.chdir(WORK_DIR)

    from configparser import ConfigParser

    app_config = ConfigParser()
    app_config.optionxform = str
    app_config_path = os.path.join(WORK_DIR, "app.conf")
    if os.path.exists(app_config_path):
        log.info(f"Loading application configuration from {app_config_path}")
        app_config.read([app_config_path])
        device_name = app_config.get("app", "device_name")
        builtins.DEVICE_NAME = device_name  # type: ignore
        device_name_base = device_name
        device_name_parts = device_name.split("-")
        if len(device_name_parts) > 2:
            # throw away any suffixes
            device_name_base = "-".join(device_name_parts[0:2])
        builtins.DEVICE_NAME_BASE = device_name_base  # type: ignore
    else:
        log.warning(
            f'Setting builtins DEVICE_NAME and DEVICE_NAME_BASE to "{APP_NAME}" due to missing configuration.'
        )
        builtins.DEVICE_NAME = APP_NAME
        builtins.DEVICE_NAME_BASE = APP_NAME
    builtins.APP_CONFIG = app_config  # type: ignore

    # 1Password credentials
    creds = None
    app_creds_config = None
    op_connect_server_env = "OP_CONNECT_HOST"
    if op_connect_server_env in os.environ:
        if hasattr(builtins, "creds_config"):
            try:
                app_creds_config = builtins.creds_config
                import onepasswordconnectsdk
                from onepasswordconnectsdk.client import (
                    Client,
                    new_client_from_environment,
                )

                creds_client: Client = new_client_from_environment()
                creds_vaults = creds_client.get_vaults()
                creds_vault_id = os.environ["OP_VAULT"]
                op_connect_server = os.environ[op_connect_server_env]
                vault_found = False
                if creds_vaults:
                    for vault in creds_vaults:
                        log.info(
                            f"Credential vault on 1Password server {op_connect_server} {vault.name} ({vault.id}) contains {vault.items} credentials."
                        )
                        if creds_vault_id == vault.id:
                            vault_found = True
                if not vault_found:
                    log.error(
                        f"No vault matching ID {creds_vault_id} found on 1Password server {op_connect_server}. See https://github.com/1Password/connect-sdk-python/"
                    )
                    sys.exit(1)
                creds = onepasswordconnectsdk.load(
                    client=creds_client, config=app_creds_config
                )
                builtins.creds = creds  # type: ignore
                builtins.creds_vault_id = creds_vault_id  # type: ignore
            except ModuleNotFoundError:
                log.error(
                    "1Password configuration is set but onepasswordconnectsdk is not available or missing from package configuration."
                )
        else:
            log.warning(
                "Assign CredsConfig to builtins.creds_config in __main__ to enable 1Password credential services."
            )
    else:
        log.warning(
            f"Set environment variable {op_connect_server_env} to enable 1Password credential services."
        )

    # Sentry
    if app_creds_config and hasattr(app_creds_config, "sentry_dsn"):
        integrations = []
        if hasattr(builtins, "SENTRY_EXTRAS"):
            integrations = builtins.SENTRY_EXTRAS  # type: ignore
        else:
            log.warning(
                "Define a list builtins.SENTRY_EXTRAS in __main__ to enable Sentry.io extras."
            )
        sentry_environment = None
        if hasattr(builtins, "SENTRY_ENVIRONMENT"):
            sentry_environment = builtins.SENTRY_ENVIRONMENT  # type: ignore
        sentry_default_integrations = True
        if hasattr(builtins, "SENTRY_DEFAULT_INTEGRATIONS"):
            sentry_default_integrations = builtins.SENTRY_DEFAULT_INTEGRATIONS  # type: ignore
        import sentry_sdk

        sentry_sdk.init(
            dsn=creds.sentry_dsn,  # type: ignore
            environment=sentry_environment,  # type: ignore
            integrations=integrations,
            default_integrations=sentry_default_integrations,
        )
    else:
        log.warning(
            "Add sentry_dsn to CredsConfig in __main__ to enable Sentry.io ticketing."
        )

    # Cronitor
    if app_creds_config and hasattr(app_creds_config, "cronitor_token"):
        import cronitor

        cronitor.api_key = creds.cronitor_token  # type: ignore
    else:
        log.warning(
            "Add cronitor_token to CredsConfig in __main__ to enable Cronitor.io monitoring."
        )

    # ZMQ helpers
    URL_WORKER_APP = "inproc://app"
    builtins.URL_WORKER_APP = URL_WORKER_APP  # type: ignore
    URL_WORKER_PUBLISHER = "inproc://publisher"
    builtins.URL_WORKER_PUBLISHER = URL_WORKER_PUBLISHER  # type: ignore
