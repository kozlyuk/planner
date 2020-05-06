from datetime import datetime
from dateutil.rrule import rrule, MONTHLY

from analytics.tasks import save_bonus

def months(start_month, start_year, end_month, end_year):
    start = datetime(start_year, start_month, 1)
    end = datetime(end_year, end_month, 1)
    return [d for d in rrule(MONTHLY, dtstart=start, until=end)]

for month in months(1, 2015, 6, 2020):
    save_bonus(month.month, month.year)
