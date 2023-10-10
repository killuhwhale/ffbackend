from datetime import datetime

import pytz
from instafitAPI.settings import env
import os


def get_env(key):
    if env(key):
        return env(key)
    return os.getenv(key, None)

def preserve_day(local_date, user_tz):
    """Preserves user's date and modifies the TZ to UTC.

        User's for_date -> replace TZ with UTC

    """
    local_datetime = datetime.strptime(local_date, "%Y-%m-%d")
    user_timezone = pytz.timezone(user_tz)
    localized_dt = user_timezone.localize(local_datetime)

    # Convert this to UTC without changing the day, month, or year
    return localized_dt.astimezone(pytz.utc)

def rev_preserve_day(preserved_date, user_tz):
    """Reverse preseve day to repalce the UTC TZ with the user's TZ"""
    stored_utc_datetime = datetime.strptime(preserved_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)

    # User's timezone
    user_timezone = pytz.timezone(user_tz)

    # Convert the UTC datetime to user's local timezone
    return stored_utc_datetime.astimezone(user_timezone)