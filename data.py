import logging
import simplejson as json
import umsgpack

from .datetime import make_timestamp


log = logging.getLogger(APP_NAME)


def make_payload(timestamp=None, data=None, msgpack=True):
    payload = {'timestamp': make_timestamp(timestamp=timestamp, make_string=True)}
    if data is not None and len(data) > 0:
        payload['data'] = data
    if log.level == logging.DEBUG:
        try:
            log.debug(json.dumps(payload))
        except (TypeError, UnicodeDecodeError):
            log.exception('Cannot JSON-encode payload for logging.')
    if msgpack:
        return umsgpack.packb(payload)
    return payload