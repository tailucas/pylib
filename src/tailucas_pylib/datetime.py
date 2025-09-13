import logging
from datetime import datetime
from typing import Optional, Union
import dateutil.parser
import pytz
from dateutil import tz

from .config import log


def make_timestamp(timestamp: Optional[Union[float,int,str,datetime]]=None, as_tz=pytz.utc) -> datetime:
    if isinstance(timestamp, float) or isinstance(timestamp, int):
        timestamp = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    elif isinstance(timestamp, str):
        try:
            log.debug(f"Attempting to parse timestamp {timestamp}")
            timestamp = dateutil.parser.parse(timestamp)
            log.debug(f"Parsed timestamp is {timestamp}")
        except ValueError:
            # try integer representation
            try:
                timestamp = datetime.fromtimestamp(int(timestamp), tz=pytz.utc) # type: ignore
                log.debug(f"Parsed integer timestamp is {timestamp}")
            except ValueError:
                log.exception(f"Unable to parse {timestamp}. Using 'now'.")
                timestamp = None
    if timestamp is None:
        timestamp = datetime.now()
        log.debug(f'Generated new timestamp {timestamp}...')
    if timestamp.tzinfo is None: # type: ignore
        local_tz = tz.tzlocal()
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz) # type: ignore
        log.debug(f"Applying local timezone {timestamp.tzname()} to timestamp {timestamp} because no TZ is set.")
        # now adjust to requested TZ
        new_timestamp = timestamp.astimezone(tz=as_tz)
        log.debug(f'{timestamp} adjusted to {new_timestamp} ({timestamp.tzname()} to {as_tz})')
        timestamp = new_timestamp
    log.debug(f"Final timestamp {timestamp}")
    return timestamp # type: ignore


def make_iso_timestamp(timestamp: Optional[Union[float,int,str,datetime]]=None, as_tz=pytz.utc) -> str:
    iso_timestamp = make_timestamp(timestamp=timestamp, as_tz=as_tz).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    log.debug(f"ISO timestamp {iso_timestamp}")
    return iso_timestamp


def make_unix_timestamp(timestamp: Optional[Union[float,int,str,datetime]]=None, as_tz=pytz.utc) -> int:
    return int(
        (
            make_timestamp(timestamp=timestamp, as_tz=as_tz) - datetime(1970, 1, 1, tzinfo=as_tz)
        ).total_seconds()
    )
