import logging
import simplejson as json
import umsgpack

from pathlib import Path
from .datetime import make_timestamp


log = logging.getLogger(Path(__file__).stem)


def make_payload(timestamp=None, data=None):
    payload = {'timestamp': make_timestamp(timestamp=timestamp, make_string=True)}
    if data is not None and len(data) > 0:
        payload['data'] = data
    try:
        log.debug(json.dumps(payload))
    except TypeError:
        log.exception('Cannot JSON-encode {}'.format(payload))
    return umsgpack.packb(payload)