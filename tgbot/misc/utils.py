import datetime
import decimal
from typing import Union, Tuple


def first_day_of_month(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    return any_day.replace(day=1)


def last_day_of_month(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    # this will never fail
    # get close to the end of the month for any day, and add 4 days 'over'
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month,
    # or said programattically said, the previous day of the first of next month
    return next_month - datetime.timedelta(days=next_month.day)


def first_day_of_week(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    weekday = any_day.weekday()
    return any_day - datetime.timedelta(days=weekday)


def last_day_of_week(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    weekday = any_day.weekday()
    return any_day + datetime.timedelta(days=6 - weekday)


def first_day_of_decade(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    decade = (any_day.day - 1) // 10
    return any_day.replace(day=1) + datetime.timedelta(days=10 * decade)


def last_day_of_decade(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    decade = (any_day.day - 1) // 10
    if decade < 2:
        return any_day.replace(day=10) + datetime.timedelta(days=10 * decade)
    return last_day_of_month(any_day)


def first_day_of_quarter(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    quarter = (any_day.month - 1) // 3
    return any_day.replace(month=1 + 3 * quarter, day=1)


def last_day_of_quarter(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    quarter = (any_day.month - 1) // 3
    return last_day_of_month(any_day.replace(month=3 + 3 * quarter, day=1))


def first_day_of_half_year(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    return any_day.replace(month=1, day=1) if any_day.month <= 6 else any_day.replace(month=7, day=1)


def last_day_of_half_year(any_day: Union[datetime.datetime, datetime.date]) -> datetime.date:
    return any_day.replace(month=6, day=30) if any_day.month < 6 else any_day.replace(month=12, day=31)


def date_range(any_day: Union[datetime.datetime, datetime.date],
               range_code: str = 'w') -> Tuple[datetime.date, datetime.date]:
    if isinstance(any_day, datetime.datetime):
        any_day = any_day.date()
    if range_code not in ['w', 'd', 'm', 'q', 'h', 'y']:
        return any_day, any_day
    if range_code == 'w':
        return first_day_of_week(any_day), last_day_of_week(any_day)
    if range_code == 'd':
        return first_day_of_decade(any_day), last_day_of_decade(any_day)
    if range_code == 'm':
        return first_day_of_month(any_day), last_day_of_month(any_day)
    if range_code == 'q':
        return first_day_of_quarter(any_day), last_day_of_quarter(any_day)
    if range_code == 'h':
        return first_day_of_half_year(any_day), last_day_of_half_year(any_day)
    if range_code == 'y':
        return any_day.replace(month=1, day=1), any_day.replace(month=12, day=31)


def remove_extra_spaces(text: str) -> str:
    clean_text = ' '.join([t for t in text.split(' ') if t])
    return "\n".join([t for t in clean_text.split('\n') if t])


def format_float(value: Union[int, float, decimal.Decimal], pre=4) -> str:
    return f"{value:<+,.{pre}f}".replace(",", " ")


def format_decimal(value: Union[int, float, decimal.Decimal], pre=8):
    s = f"{value:.{pre}f}"
    return s.rstrip('0').rstrip('.') if '.' in s else s


def value_to_decimal(value, decimal_places: int = 8) -> decimal.Decimal:
    decimal.getcontext().rounding = decimal.ROUND_HALF_UP  # define rounding method
    return decimal.Decimal(str(float(value))).quantize(decimal.Decimal('1e-{}'.format(decimal_places)))
