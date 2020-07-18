import simplejson as json
import umsgpack


def make_payload(timestamp=None, data=None):
    payload = {'timestamp': make_timestamp(timestamp, True)}
    if data is not None and len(data) > 0:
        payload['data'] = data
    log.debug(json.dumps(payload))
    return umsgpack.packb(payload)