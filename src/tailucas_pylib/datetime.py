from datetime import datetime

import dateutil.parser
import pytz
from dateutil import tz

from . import log


def make_timestamp(
    timestamp: float | int | str | datetime | None = None, as_tz=pytz.utc
) -> datetime:
    if isinstance(timestamp, float | int):
        timestamp = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    elif isinstance(timestamp, str):
        try:
            log.debug("Attempting to parse timestamp", extra={"timestamp": timestamp})
            timestamp = dateutil.parser.parse(timestamp)
            log.debug("Parsed timestamp", extra={"timestamp": str(timestamp)})
        except ValueError:
            # try integer representation
            try:
                timestamp = datetime.fromtimestamp(int(timestamp), tz=pytz.utc)  # type: ignore
                log.debug("Parsed integer timestamp", extra={"timestamp": str(timestamp)})
            except ValueError:
                log.exception(
                    "Unable to parse timestamp. Using 'now'.", extra={"timestamp": timestamp}
                )
                timestamp = None
    if timestamp is None:
        timestamp = datetime.now()
        log.debug("Generated new timestamp", extra={"timestamp": str(timestamp)})
    if timestamp.tzinfo is None:  # type: ignore
        local_tz = tz.tzlocal()
        # we use the default specific to the physical locality of the devices
        timestamp = timestamp.replace(tzinfo=local_tz)  # type: ignore
        log.debug(
            "Applying local timezone to timestamp because no TZ is set",
            extra={"timezone": timestamp.tzname(), "timestamp": str(timestamp)},  # type: ignore[union-attr]
        )
        # now adjust to requested TZ
        new_timestamp = timestamp.astimezone(tz=as_tz)  # type: ignore[union-attr]
        log.debug(
            "Timestamp adjusted to requested timezone",
            extra={
                "timestamp": str(timestamp),
                "new_timestamp": str(new_timestamp),
                "from_timezone": timestamp.tzname(),  # type: ignore[union-attr]
                "to_timezone": str(as_tz),
            },
        )
        timestamp = new_timestamp
    log.debug("Final timestamp", extra={"timestamp": str(timestamp)})
    return timestamp  # type: ignore


def make_iso_timestamp(
    timestamp: float | int | str | datetime | None = None, as_tz=pytz.utc
) -> str:
    iso_timestamp = (
        make_timestamp(timestamp=timestamp, as_tz=as_tz)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    log.debug("ISO timestamp", extra={"iso_timestamp": iso_timestamp})
    return iso_timestamp


def make_unix_timestamp(
    timestamp: float | int | str | datetime | None = None, as_tz=pytz.utc
) -> int:
    return int(
        (
            make_timestamp(timestamp=timestamp, as_tz=as_tz) - datetime(1970, 1, 1, tzinfo=as_tz)
        ).total_seconds()
    )
