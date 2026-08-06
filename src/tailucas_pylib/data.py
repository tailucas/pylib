import logging

import umsgpack as msgpack

from . import log
from .datetime import make_iso_timestamp


def make_payload(timestamp=None, data=None, pack=True):
    payload = {"timestamp": make_iso_timestamp(timestamp=timestamp)}
    if data is not None and len(data) > 0:
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload["data"] = data
    if log.level == logging.DEBUG:
        log.debug("Payload created", extra={"payload": payload})
    if pack:
        return msgpack.packb(payload)
    return payload
