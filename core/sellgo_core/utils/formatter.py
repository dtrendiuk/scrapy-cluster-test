import re


def formatted_date(date):
    return re.sub(r'[:\.\-]+', '_', date.isoformat())
