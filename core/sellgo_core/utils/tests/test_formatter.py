import datetime
import re

from sellgo_core.utils.formatter import formatted_date


def test_formatted_date():
    datetime_now = datetime.datetime.now()
    date = formatted_date(datetime_now)

    assert date is not None
    assert re.search(r'\d{4}[_/]\d{2}[_/]\d{2}T\d{2}[_/]\d{2}[_/]\d{2}[_/]\d{6}', date)
