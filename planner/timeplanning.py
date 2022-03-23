from datetime import  datetime, timedelta, time
import businesstimedelta
import holidays as pyholidays
from django.apps import apps


# Execution statuses
ToDo = 'IW'
InProgress = 'IP'
Done = 'HD'
OnChecking = 'OC'

# Define a working day
workday = businesstimedelta.WorkDayRule(
    start_time=time(9),
    end_time=time(18),
    working_days=[0, 1, 2, 3])

friday = businesstimedelta.WorkDayRule(
    start_time=time(9),
    end_time=time(18),
    working_days=[4])

lunchbreak = businesstimedelta.LunchTimeRule(
    start_time=time(12),
    end_time=time(13),
    working_days=[0, 1, 2, 3, 4])

businesshrs = businesstimedelta.Rules([workday, friday, lunchbreak])

def queue_task(task, current_task_finish):
    # get task duration in hours
    if task.planned_start and task.planned_finish:
        businesshrsdelta = businesshrs.difference(task.planned_start, task.planned_finish)
        task_duration = timedelta(hours=businesshrsdelta.hours, seconds=businesshrsdelta.seconds)
    elif task.subtask.add_to_schedule:
        task_duration = task.subtask.duration
    else:
        task_duration = timedelta(0)
    # set planned start and finish
    business_hour = businesstimedelta.BusinessTimeDelta(businesshrs, hours=1)
    task.planned_start = current_task_finish + business_hour - business_hour
    task.planned_finish = task.planned_start + businesstimedelta.BusinessTimeDelta(
                                                businesshrs,
                                                hours=task_duration.days*24+task_duration.seconds/3600
                                                )
    # remove tzinfo
    task.planned_start = task.planned_start.replace(tzinfo=None)
    task.planned_finish = task.planned_finish.replace(tzinfo=None)

    return task


def recalc_queue(employee):
    """ recalc queue for executors whem subtask changed"""
    execution_model = apps.get_model('planner.Execution')
    tasks_to_do = employee.execution_set.filter(exec_status=ToDo)
    task_in_progress = employee.execution_set.filter(exec_status=InProgress).order_by('planned_finish').last()
    current_task_finish = task_in_progress.planned_finish \
        if task_in_progress and task_in_progress.planned_finish else datetime.now()

    tasks = []
    # plan queued tasks
    for task in tasks_to_do.filter(planned_start__isnull=False).order_by('planned_start'):
        queued_task = queue_task(task, current_task_finish)
        tasks.append(queued_task)
        current_task_finish = queued_task.planned_finish

    # plan not queued tasks
    for task in tasks_to_do.filter(planned_start__isnull=True):
        queued_task = queue_task(task, current_task_finish)
        tasks.append(queued_task)
        current_task_finish = queued_task.planned_finish

    # perform bulk_update
    execution_model.objects.bulk_update(tasks, ['planned_start', 'planned_finish'])
