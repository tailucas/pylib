import logging
import builtins
import dateutil.parser
import pytz

from datetime import datetime, timedelta
from dateutil import tz

builtins.ISO_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

log = logging.getLogger(APP_NAME)

def is_list(value):
    return isinstance(value, list)


def make_timestamp(timestamp=None, as_tz=pytz.utc, make_string=False):
    if timestamp is None:
        timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
    elif isinstance(timestamp, float) or isinstance(timestamp, int):
        timestamp = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
    elif isinstance(timestamp, str):
        try:
            timestamp = dateutil.parser.parse(timestamp)
            log.debug('Parsed timestamp is {}'.format(timestamp))
        except ValueError:
            try:
                timestamp = datetime.utcfromtimestamp(int(timestamp)).replace(tzinfo=pytz.utc)
                log.debug('Parsed integer timestamp is {}'.format(timestamp))
            except ValueError:
                raise RuntimeError("Unknown date/time type: '{}'".format(timestamp))
    if timestamp.tzinfo is None:
        local_tz = tz.tzlocal()
        log.debug('{}: fixed to local time {}'.format(timestamp, local_tz))
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz)
    if timestamp.tzinfo != as_tz:
        # now adjust to requested TZ
        new_timestamp = timestamp.astimezone(tz=as_tz)
        log.debug('{} adjusted to {} ({} to {})'.format(timestamp, new_timestamp, timestamp.tzinfo, as_tz))
        timestamp = new_timestamp
    log.debug('Using timestamp {}'.format(timestamp))
    if make_string:
        return timestamp.strftime(ISO_DATE_FORMAT)
    return timestamp


def parse_datetime(value=None, as_tz=pytz.utc):
    timestamp = datetime.utcnow().replace(tzinfo=as_tz)
    if value is None:
        return timestamp
    if isinstance(value, str):
        try:
            timestamp = dateutil.parser.parse(value)
            log.debug('Parsed timestamp is {}'.format(timestamp))
        except ValueError:
            log.exception("Cannot parse date-like string {}. Defaulting to '{}'.".format(value, timestamp))
    elif isinstance(value, datetime):
        timestamp = value
    else:
        raise RuntimeError("Unknown date/time type: '{}'".format(value))
    # ensure that some timezone information is present
    if timestamp.tzinfo is None:
        local_tz = tz.tzlocal()
        log.debug('{}: setting to local time {}'.format(timestamp, local_tz))
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz)
    if timestamp.tzinfo != as_tz:
        # now adjust to requested TZ
        log.debug('{}: setting to {} from {}'.format(timestamp, as_tz, timestamp.tzinfo))
        timestamp = timestamp.astimezone(tz=as_tz)
    return timestamp
