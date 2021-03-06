import datetime
from datetime import date

from dateutil.relativedelta import relativedelta

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
PATH_TIME_FORMAT = '%Y_%m_%d_%H_%M_%S'


def get_time() -> datetime:
    return datetime.datetime.now()


def format_datetime(val: datetime, time_format: str) -> str:
    return val.strftime(time_format)


def get_today() -> date:
    """return today's date"""

    return datetime.date.today()


def get_first_day_next_month() -> date:
    today = get_today()
    month = today.month + 1 if today.month < 12 else 1
    year = today.year if today.month < 12 else today.year + 1
    return today.replace(year=year, month=month, day=1)


def get_months_back(number_of_months):
    """
    returns datetime for first of month 'number_of_months' back
    :param number_of_months:
    :return:
    """
    return (get_today() - relativedelta(months=+number_of_months)).replace(day=1)


def get_days_back(number_of_days):
    return get_today() - relativedelta(days=+number_of_days)
