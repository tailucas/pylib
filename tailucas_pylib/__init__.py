import builtins
import logging.handlers
import os.path
import sys


if hasattr(builtins, 'PYTEST'):
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
    # define the log format
    formatter = logging.Formatter('%(name)s %(threadName)s [%(levelname)s] %(message)s')
    log_handler = None
    if os.path.exists('/dev/log'):
        log_handler = logging.handlers.SysLogHandler(address='/dev/log')
        log_handler.setFormatter(formatter)
        log.addHandler(log_handler)
    if sys.stdout.isatty() or ('SUPERVISOR_ENABLED' in os.environ and log_handler is None):
        log.warning("Using console logging because there is a tty or under supervisord.")
        log_handler = logging.StreamHandler(stream=sys.stdout)
        log_handler.setFormatter(formatter)
        log.addHandler(log_handler)
    builtins.log = log  # type: ignore
    builtins.log_handler = log_handler  # type: ignore

    # use parent of this module's top-level __init__.py
    from pathlib import Path
    app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
    log.debug(f'Running from {app_path}, using working directory {WORK_DIR}')
    # assert working directory for assumptions made (such as PyDrive)
    current_work_dir = os.getcwd()
    if current_work_dir != WORK_DIR:
        log.warning(f'Changing working directory from {current_work_dir} to {WORK_DIR}')
        os.chdir(WORK_DIR)

    from configparser import ConfigParser
    app_config = ConfigParser()
    app_config.optionxform = str
    app_config_path = os.path.join(WORK_DIR, f'app.conf')
    if os.path.exists(app_config_path):
        log.info(f'Loading application configuration from {app_config_path}')
        app_config.read([app_config_path])
        device_name = app_config.get('app', 'device_name')
        builtins.DEVICE_NAME = device_name  # type: ignore
        device_name_base = device_name
        device_name_parts = device_name.split('-')
        if len(device_name_parts) > 2:
            # throw away any suffixes
            device_name_base = '-'.join(device_name_parts[0:2])
        builtins.DEVICE_NAME_BASE = device_name_base  # type: ignore
    else:
        log.warning(f'Setting builtins DEVICE_NAME and DEVICE_NAME_BASE to "{APP_NAME}" due to missing configuration.')
        builtins.DEVICE_NAME = APP_NAME
        builtins.DEVICE_NAME_BASE = APP_NAME
    builtins.APP_CONFIG = app_config  # type: ignore

    # 1Password credentials
    creds = None
    app_creds_config = None
    op_connect_server_env = 'OP_CONNECT_SERVER'
    if op_connect_server_env in os.environ:
        if hasattr(builtins, 'creds_config'):
            app_creds_config = builtins.creds_config
            import onepasswordconnectsdk
            from onepasswordconnectsdk.client import (
                Client,
                new_client_from_environment
            )
            op_connect_server = os.environ[op_connect_server_env]
            creds_client: Client = new_client_from_environment(url=op_connect_server)
            creds_vaults = creds_client.get_vaults()
            if creds_vaults:
                for vault in creds_vaults:
                    log.info(f"Credential vault {vault.name} contains {vault.items} credentials.")
            else:
                log.error(f'No vaults found on 1Password server {op_connect_server}. Fix or remove environment variable {op_connect_server_env}.')
                sys.exit(1)
            creds = onepasswordconnectsdk.load(client=creds_client, config=app_creds_config)
            builtins.creds = creds  # type: ignore
        else:
            log.warning(f'Assign CredsConfig to builtins.creds_config in __main__ to enable 1Password credential services.')
    else:
        log.warning(f'Set environment variable {op_connect_server_env} to enable 1Password credential services.')

    # Sentry
    if app_creds_config and hasattr(app_creds_config, 'sentry_dsn'):
        integrations = []
        if hasattr(builtins, 'SENTRY_EXTRAS'):
            integrations = builtins.SENTRY_EXTRAS  # type: ignore
        else:
            log.warning(f'Define a list builtins.SENTRY_EXTRAS in __main__ to enable Sentry.io extras.')
        sentry_environment = None
        if hasattr(builtins, 'SENTRY_ENVIRONMENT'):
            sentry_environment = builtins.SENTRY_ENVIRONMENT  # type: ignore
        import sentry_sdk
        sentry_sdk.init(
            dsn=creds.sentry_dsn,  # type: ignore
            environment=sentry_environment,  # type: ignore
            integrations=integrations
        )
    else:
        log.warning(f'Add sentry_dsn to CredsConfig in __main__ to enable Sentry.io ticketing.')

    # Cronitor
    if app_creds_config and hasattr(app_creds_config, 'cronitor_token'):
        import cronitor
        cronitor.api_key = creds.cronitor_token  # type: ignore
    else:
        log.warning(f'Add cronitor_token to CredsConfig in __main__ to enable Cronitor.io monitoring.')

    # ZMQ helpers
    URL_WORKER_APP = 'inproc://app'
    builtins.URL_WORKER_APP = URL_WORKER_APP  # type: ignore
    URL_WORKER_PUBLISHER = 'inproc://publisher'
    builtins.URL_WORKER_PUBLISHER = URL_WORKER_PUBLISHER  # type: ignore