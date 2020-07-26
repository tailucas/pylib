import logging
import simplejson as json
import umsgpack

from .datetime import make_timestamp

log = logging.getLogger(APP_NAME)

def make_payload(timestamp=None, data=None):
    payload = {'timestamp': make_timestamp(timestamp=timestamp, make_string=True)}
    if data is not None and len(data) > 0:
        payload['data'] = data
    log.debug(json.dumps(payload))
    return umsgpack.packb(payload)