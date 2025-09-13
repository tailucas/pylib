import pytest

from datetime import datetime, timedelta
import pytz
from pytz import timezone

from tailucas_pylib.datetime import (
    make_timestamp,
    make_iso_timestamp,
    make_unix_timestamp,
)


@pytest.fixture(scope="session")
def setup_datetime_datetime_notz():
    return datetime(1985, 10, 26, 1, 21, 0)


@pytest.fixture(scope="session")
def setup_datetime_datetime():
    return datetime(1985, 10, 26, 1, 21, 0, tzinfo=pytz.utc)


@pytest.fixture(scope="session")
def setup_datetime_string():
    return "1985-10-26T01:21:00-00:00"


def test_make_timestamp(
    setup_datetime_datetime_notz, setup_datetime_datetime, setup_datetime_string
):
    assert make_timestamp() is not None
    assert (
        make_timestamp(timestamp=setup_datetime_datetime_notz)
        == setup_datetime_datetime
    )
    edt_timestamp: datetime = make_timestamp(
        timestamp=setup_datetime_datetime_notz, as_tz=timezone("US/Eastern")
    )
    assert edt_timestamp.year == 1985
    assert edt_timestamp.month == 10
    assert edt_timestamp.day == 25
    assert edt_timestamp.hour == 21
    assert edt_timestamp.minute == 21
    assert edt_timestamp.second == 0
    assert edt_timestamp.tzname() == "EDT"
    assert edt_timestamp.utcoffset() == timedelta(hours=-4)
    assert make_timestamp(timestamp=setup_datetime_datetime) == setup_datetime_datetime
    assert make_timestamp(timestamp=setup_datetime_string) == setup_datetime_datetime


def test_make_iso_timestamp(
    setup_datetime_datetime_notz, setup_datetime_datetime, setup_datetime_string
):
    assert make_iso_timestamp() is not None
    assert (
        make_iso_timestamp(timestamp=setup_datetime_datetime) == "1985-10-26T01:21:00Z"
    )
    assert make_iso_timestamp(timestamp=setup_datetime_string) == "1985-10-26T01:21:00Z"
    assert (
        make_iso_timestamp(
            timestamp=setup_datetime_datetime_notz, as_tz=timezone("US/Eastern")
        )
        == "1985-10-25T21:21:00-04:00"
    )


def test_make_unix_timestamp(setup_datetime_datetime, setup_datetime_string):
    assert make_unix_timestamp() > 0
    assert make_unix_timestamp(timestamp=setup_datetime_datetime) == 499137660
    assert make_unix_timestamp(timestamp=setup_datetime_string) == 499137660
