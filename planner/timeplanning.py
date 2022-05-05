from datetime import  datetime, timedelta, time
import businesstimedelta
from django.db.models import F
import holidays as pyholidays
from django.apps import apps


# Execution statuses
ToDo = 'IW'
InProgress = 'IP'
Done = 'HD'
OnChecking = 'OC'
Sent = 'ST'

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
    start_time=time(13),
    end_time=time(14),
    working_days=[0, 1, 2, 3, 4])

ua_holidays = pyholidays.country_holidays('UA')
holidays = businesstimedelta.HolidayRule(ua_holidays)

businesshrs = businesstimedelta.Rules([workday, friday, lunchbreak, holidays])

def calc_businesshrsdiff(start_time, finish_time):
    businesshrsdelta = businesshrs.difference(start_time, finish_time)
    return timedelta(hours=businesshrsdelta.hours, seconds=businesshrsdelta.seconds)

def calc_businesstimedelta(start_time, task_duration):
    finish_time = start_time + businesstimedelta.BusinessTimeDelta(
        businesshrs,
        hours=task_duration.days*24+task_duration.seconds/3600
        )
    return finish_time.replace(tzinfo=None)

def merge_fixed_periods(tasks_to_do_fixed):
    """ merge fixed periods from tasks_to_do_fixed """
    fixed_periods = []
    for task in tasks_to_do_fixed:
        if not fixed_periods:
            fixed_periods.append([task['planned_start'], task['planned_finish']])
            continue
        for period in fixed_periods:
            start_in_period = period[0] <= task['planned_start'] <= period[1]
            finish_in_period = period[0] <= task['planned_finish'] <= period[1]
            if start_in_period and finish_in_period:
                break
            elif start_in_period and not finish_in_period:
                period[1] = task['planned_finish']
            elif not start_in_period and finish_in_period:
                period[0] = task['planned_start']
            elif task['planned_start'] < period[0] and task['planned_finish'] > period[1]:
                period[0] = task['planned_start']
                period[1] = task['planned_finish']
            else:
                fixed_periods.append([task['planned_start'], task['planned_finish']])
                break
    return fixed_periods

def add_interruption(task, fixed_periods, task_duration):
    """ check if task overlap with tasks_to_do_fixed """
    task.interruption = timedelta(0)
    for period in fixed_periods:
        start_in_period = period[0] <= task.planned_start < period[1]
        finish_in_period = period[0] < task.planned_finish <= period[1]
        if start_in_period:
            task.planned_start = period[1]
            task.planned_finish = calc_businesstimedelta(task.planned_start, task_duration)
            return task
        elif finish_in_period or \
            task.planned_start < period[0] and task.planned_finish > period[1]:
            task.interruption = calc_businesshrsdiff(period[0], period[1])
            return task
    return task

def get_task_duration(task):
    """ get task duration in hours """
    if task.planned_start and task.planned_finish and task.planned_start < task.planned_finish:
        return calc_businesshrsdiff(task.planned_start, task.planned_finish)
    elif task.subtask.add_to_schedule:
        return task.subtask.duration
    return timedelta(0)

def queue_task(task, last_task_finish, fixed_periods):
    """ set planned start and finish """
    task_duration = get_task_duration(task)
    business_hour = businesstimedelta.BusinessTimeDelta(businesshrs, hours=1)
    task.planned_start = last_task_finish + business_hour - business_hour
    task.planned_start = task.planned_start.replace(tzinfo=None)
    task.planned_finish = calc_businesstimedelta(task.planned_start, task_duration)

    return add_interruption(task, fixed_periods, task_duration)

def get_last_task_finish(employee):
    """ calculate last task finish time """
    last_task = employee.execution_set.filter(exec_status__in=[Done,OnChecking],
                                              task__exec_status__in=[InProgress,Done,Sent],
                                              subtask__add_to_schedule=True
                                              ) \
                                      .order_by('planned_finish').last()
    if last_task and last_task.planned_finish:
        return last_task.planned_finish_with_interruption
    return datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)

def recalc_queue(employee):
    """ recalc queue for executors whem subtask changed"""
    execution_model = apps.get_model('planner.Execution')
    tasks_to_do = employee.execution_set.filter(exec_status__in=[ToDo, InProgress],
                                                subtask__add_to_schedule=True,
                                                task__exec_status__in=[ToDo,InProgress]
                                                )
    tasks_to_do_fixed = tasks_to_do.filter(fixed_date=True).values('planned_start', 'planned_finish')
    fixed_periods = merge_fixed_periods(tasks_to_do_fixed)
    tasks_to_do_not_fixed = tasks_to_do.filter(fixed_date=False) \
                                       .order_by('exec_status', F('planned_start').asc(nulls_last=True))

    last_task_finish = get_last_task_finish(employee)

    tasks = []
    # plan queued tasks
    for task in tasks_to_do_not_fixed:
        queued_task = queue_task(task, last_task_finish, fixed_periods)
        tasks.append(queued_task)
        last_task_finish = queued_task.planned_finish_with_interruption

    # perform bulk_update
    execution_model.objects.bulk_update(tasks, ['planned_start', 'planned_finish', 'interruption'])
