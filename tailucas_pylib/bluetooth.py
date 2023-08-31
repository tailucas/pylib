import logging
from .process import exec_cmd

from sentry_sdk import capture_exception


log = logging.getLogger(APP_NAME)  # type: ignore


def bluetooth_init():
    # first test for a Bluetooth adaptor and format this type of output
    # Devices:
    # hci0    00:09:DD:50:17:18
    out, err, rc = exec_cmd(['hcitool', 'dev'])
    if rc != 0 or out is None:
        raise RuntimeError(f'Cannot query hcitool to find Bluetooth adaptors: {out} {err}')
    hcitool = out.decode().rstrip().split('\n')
    if len(hcitool) < 2:
        raise RuntimeError('No Bluetooth adaptors found using hcitool.')
    for line in hcitool[1:]:
        adapter = ' '.join(line.split())
        log.info(f'Bluetooth adaptor found: {adapter}')


def l2ping(owner, device):
    log.debug(f'l2ping {owner} @ {device}...')
    out, err, rc = exec_cmd(['sudo', '/usr/bin/l2ping', '-t1', '-c1', device])
    l2pingo = None
    if out is not None:
        l2pingo = out.decode()
    else:
        raise RuntimeError(f'Cannot perform l2ping of {owner} @ {device}: {err}')
    if rc == 0:
        log.debug(f'l2ping output: {l2pingo}')
        return l2pingo
    else:
        log.debug(f'Non-zero exit {rc} for l2ping output: {l2pingo} {err}')
    return None


def ping_bluetooth_devices(owner_device_list):
    owner_devices = list()
    ping_response = dict()
    try:
        log.debug(owner_device_list)
        if type(owner_device_list) is str:
            owner_device_string = owner_device_list.split(',')
            for ods in owner_device_string:
                od = ods.split(';')
                owner_devices.append((od[0], od[1]))
        elif type(owner_device_list) is tuple:
            owner_devices.append(owner_device_list)
        elif type(owner_device_list) is list:
            owner_devices = owner_device_list
        else:
            raise f"Unsupported type {type(owner_device_list)} for parameters {owner_device_list}."
        log.info(f'DEBUG: l2ping using {owner_devices}.')
        for owner, device in owner_devices:
            sample_value = l2ping(owner, device)
            log.debug(f'ping response for {owner} @ {device}: {sample_value}')
            if sample_value:
                ping_response[owner] = sample_value
    except Exception:
        log.exception('ping_bluetooth_devices')
        capture_exception()
        raise

    if len(ping_response) > 0:
        return ping_response
    return None
