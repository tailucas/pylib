import logging
import dateutil.parser
import pytz

from datetime import datetime, timedelta
from dateutil import tz


log = logging.getLogger(APP_NAME)  # type: ignore


ISO_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


def is_list(value):
    return isinstance(value, list)


def make_timestamp(timestamp=None, as_tz=pytz.utc, make_string=False):
    if isinstance(timestamp, float) or isinstance(timestamp, int):
        timestamp = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
    elif isinstance(timestamp, str):
        try:
            log.debug(f'Attempting to parse timestamp {timestamp}')
            timestamp = dateutil.parser.parse(timestamp)
            log.debug(f'Parsed timestamp is {timestamp}')
        except ValueError:
            # try integer representation
            try:
                timestamp = datetime.utcfromtimestamp(int(timestamp)).replace(tzinfo=pytz.utc)
                log.debug(f'Parsed integer timestamp is {timestamp}')
            except ValueError:
                log.exception(f"Unable to parse {timestamp}. Using 'now'.")
                timestamp = None
    if timestamp is None:
        timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
    if timestamp.tzinfo is None:
        local_tz = tz.tzlocal()
        log.debug(f'{timestamp}: fixed to local time {local_tz}')
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz)
    if timestamp.tzinfo != as_tz:
        # now adjust to requested TZ
        new_timestamp = timestamp.astimezone(tz=as_tz)
        log.debug(f'{timestamp} adjusted to {new_timestamp} ({timestamp.tzinfo} to {as_tz})')
        timestamp = new_timestamp
    log.debug(f'Using timestamp {timestamp}')
    if make_string:
        return timestamp.strftime(ISO_DATE_FORMAT)  # type: ignore
    return timestamp


def make_unix_timestamp(timestamp=None):
    return int((make_timestamp(timestamp=timestamp).replace(tzinfo=None) - datetime(1970, 1, 1)).total_seconds())


def parse_datetime(value=None, as_tz=pytz.utc):
    timestamp = datetime.utcnow().replace(tzinfo=as_tz)
    if value is None:
        return timestamp
    if isinstance(value, str):
        try:
            timestamp = dateutil.parser.parse(value)
            log.debug(f'Parsed timestamp is {timestamp}')
        except ValueError:
            log.exception(f"Cannot parse date-like string {value}. Defaulting to '{timestamp}'.")
    elif isinstance(value, datetime):
        timestamp = value
    else:
        raise RuntimeError(f"Unknown date/time type: '{value}'")
    # ensure that some timezone information is present
    if timestamp.tzinfo is None:
        local_tz = tz.tzlocal()
        log.debug(f'{timestamp}: setting to local time {local_tz}')
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz)
    if timestamp.tzinfo != as_tz:
        # now adjust to requested TZ
        log.debug(f'{timestamp}: setting to {as_tz} from {timestamp.tzinfo}')
        timestamp = timestamp.astimezone(tz=as_tz)
    return timestamp
