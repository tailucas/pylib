import logging
import simplejson as json
import msgpack

from .datetime import make_timestamp


log = logging.getLogger(APP_NAME)  # type: ignore


def make_payload(timestamp=None, data=None, pack=True):
    payload = {'timestamp': make_timestamp(timestamp=timestamp, make_string=True)}
    if data is not None and len(data) > 0:
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload['data'] = data
    if log.level == logging.DEBUG:
        try:
            log.debug(json.dumps(payload))
        except (TypeError, UnicodeDecodeError):
            log.exception('Cannot JSON-encode payload for logging.')
    if pack:
        return msgpack.packb(payload)
    return payload
