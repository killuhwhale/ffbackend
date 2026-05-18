import datetime
import logging
import pytz
tz = pytz.timezone("US/Pacific")
logger = logging.getLogger(__name__)


def tz_aware_today():
    return tz.localize(datetime.datetime.today())

def tz_aware_date(yr: int, m: int, d: int):
    return tz.localize(datetime.datetime(yr,m,d))


if __name__ == "__main__":
    a = tz_aware_date(2023, 2, 5)
    b = tz_aware_today()
    logger.info("%s", a)
    logger.info("%s", b)
