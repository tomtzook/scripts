from datetime import datetime, date, tzinfo
from typing import Union

from dateutil import tz


def convert_timezone(time: Union[datetime, date],
                     source: tzinfo,
                     destination: tzinfo = tz.tzlocal()):
    as_source = time.replace(tzinfo=source)
    return as_source.astimezone(destination)
