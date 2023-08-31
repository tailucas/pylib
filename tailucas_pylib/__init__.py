import builtins
import logging.handlers
import os.path
import sys


if hasattr(builtins, 'PYTEST'):
    pass
else:
    import cronitor
    import onepasswordconnectsdk
    import sentry_sdk

    from configparser import ConfigParser
    from pathlib import Path
    from onepasswordconnectsdk.client import (
        Client,
        new_client_from_environment
    )

    from app import APP_NAME, WORK_DIR

    if sys.stdout.isatty() and os.system('systemctl status app') == 0:
        print(f"{APP_NAME} is already running. Use 'systemctl stop app' to stop first.")
        sys.exit(1)

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

    # use parent of this module's top-level __init__.py
    app_path = Path(os.path.abspath(os.path.dirname(__file__))).parent
    log.debug(f'Running from {app_path}, using working directory {WORK_DIR}')
    # assert working directory for assumptions made (such as PyDrive)
    current_work_dir = os.getcwd()
    if current_work_dir != WORK_DIR:
        log.warning(f'Changing working directory from {current_work_dir} to {WORK_DIR}')
        os.chdir(WORK_DIR)

    app_config_path = os.path.join(WORK_DIR, f'app.conf')
    app_config = ConfigParser()
    app_config.optionxform = str
    log.info(f'Loading application configuration from {app_config_path}')
    app_config.read([app_config_path])

    # credentials
    creds_client: Client = new_client_from_environment(url=os.environ['OP_CONNECT_SERVER'])
    creds_vaults = creds_client.get_vaults()
    for vault in creds_vaults:
        log.info(f"Credential vault {vault.name} contains {vault.items} credentials.")
    creds = onepasswordconnectsdk.load(client=creds_client, config=builtins.creds_config)  # pylint: disable=no-member

    sentry_sdk.init(
        dsn=creds.sentry_dsn,
        integrations=builtins.SENTRY_EXTRAS  # pylint: disable=no-member
    )
    if hasattr(creds, 'cronitor_token'):
        cronitor.api_key = creds.cronitor_token

    # update builtins
    builtins.APP_NAME = APP_NAME
    builtins.APP_PATH = WORK_DIR
    builtins.APP_CONFIG = app_config
    device_name = app_config.get('app', 'device_name')
    DEVICE_NAME = device_name
    builtins.DEVICE_NAME = device_name
    device_name_base = device_name
    device_name_parts = device_name.split('-')
    if len(device_name_parts) > 2:
        # throw away any suffixes
        device_name_base = '-'.join(device_name_parts[0:2])
    builtins.DEVICE_NAME_BASE = device_name_base
    builtins.log = log
    builtins.log_handler = log_handler
    builtins.creds_config = creds
    URL_WORKER_APP = 'inproc://app'
    builtins.URL_WORKER_APP = URL_WORKER_APP
    URL_WORKER_PUBLISHER = 'inproc://publisher'
    builtins.URL_WORKER_PUBLISHER = URL_WORKER_PUBLISHER