from datetime import datetime
from dateutil.rrule import rrule, MONTHLY

from analytics.tasks import calc_bonuses, calc_kpi

def months(start_month, start_year, end_month, end_year):
    start = datetime(start_year, start_month, 1)
    end = datetime(end_year, end_month, 1)
    return list(rrule(MONTHLY, dtstart=start, until=end))

for month in months(1, 2015, 12, 2020):
    calc_bonuses(month)
    calc_kpi(month)

print('Calculation finished')


from planner.models import Task

tasks = Task.objects.all()
for task in tasks:
    if task.sending_set.all().exists():
        task.sending_date = task.sending_set.earliest('receipt_date').receipt_date
    if task.project_type.copies_count == 0:
        task.sending_date = task.actual_finish
    task.save()

print('Calculation finished')


from planner.models import Task

tasks = Task.objects.all()
for task in tasks:
    if task.sending_set.all().exists():
        sending = task.sending_set.earliest('receipt_date').receipt_date
        if sending.month == 4 and sending.year == 2020:
            task.sending_date = sending
    if task.project_type.copies_count == 0:
        task.sending_date = task.actual_finish
    task.save()


from analytics.models import Kpi

kpies = Kpi.objects.all()
for kpi in kpies:
    kpi.delete()
