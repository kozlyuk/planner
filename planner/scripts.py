from datetime import datetime
from dateutil.rrule import rrule, MONTHLY

from analytics.tasks import calc_bonuses, calc_kpi

def months(start_month, start_year, end_month, end_year):
    start = datetime(start_year, start_month, 1)
    end = datetime(end_year, end_month, 1)
    return list(rrule(MONTHLY, dtstart=start, until=end))

for month in months(1, 2015, 12, 2020):
    calc_bonuses(period=month)
    calc_kpi(period=month)

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


from planner.models import Execution, SubTask

for execution in Execution.objects.all().order_by('-pk'):
    try:
        subtask = SubTask.objects.get(project_type=execution.task.project_type,
                                      name=execution.subtask.name)
    except:
        subtask = SubTask.objects.create(project_type=execution.task.project_type,
                                         name=execution.subtask.name,
                                         part=execution.part
                                         )
    execution.subtask = subtask
    execution.save()


from planner.models import Order, SubTask

for order in Order.objects.all().order_by('-pk'):
    try:
        subtask = SubTask.objects.get(project_type=order.task.project_type,
                                      name=order.order_name)
    except:
        subtask = SubTask.objects.create(project_type=order.task.project_type,
                                         name=order.order_name,
                                         part=0
                                         )
    order.subtask = subtask
    order.save()


from planner.models import Order, Execution

Execution.objects.filter(subtask__pk=2457).update(subtask=2349)
Order.objects.filter(subtask__pk=2457).update(subtask=2349)
