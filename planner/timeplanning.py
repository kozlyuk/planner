from datetime import  datetime, timedelta, time
from django.db.models import F
from django.apps import apps

import businesstimedelta
import holidays as pyholidays


class TimePlanner():

    # Execution statuses
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    OnChecking = 'OC'
    OnCorrection = 'CR'
    Sent = 'ST'

    def __init__(self, employee):
        self.employee = employee

        ''' Init businesshrs rules '''
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

        ua_holidays = self.__add_vacation__(pyholidays.country_holidays('UA'))
        holidays = businesstimedelta.HolidayRule(ua_holidays)

        self.businesshrs = businesstimedelta.Rules([workday, friday, lunchbreak, holidays])

    @staticmethod
    def __daterange__(start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + timedelta(n)

    @staticmethod
    def __merge_fixed_periods__(tasks_to_do_fixed):
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

    def __add_vacation__(self, holidays):
        ''' add employee's vacation to holidays '''
        try:
            vacation_model = apps.get_model('planner.Vacation')
            last_vacation = self.employee.vacation_set.latest('end_date')
            if last_vacation:
                for day in self.__daterange__(last_vacation.start_date, last_vacation.end_date):
                    holidays[day] = "Відпустка"
        except vacation_model.DoesNotExist:
            pass
        return holidays

    def calc_businesshrsdiff(self, start_time, finish_time):
        businesshrsdelta = self.businesshrs.difference(start_time, finish_time)
        return timedelta(hours=businesshrsdelta.hours, seconds=businesshrsdelta.seconds)

    def calc_businesstimedelta(self, start_time, task_duration):
        finish_time = start_time + businesstimedelta.BusinessTimeDelta(
            self.businesshrs,
            hours=task_duration.days*24+task_duration.seconds/3600
            )
        return finish_time.replace(tzinfo=None)

    def __add_interruption__(self, task, task_duration):
        """ check if task overlap with tasks_to_do_fixed """
        task.interruption = timedelta(0)
        for period in self.fixed_periods:
            start_in_period = period[0] <= task.planned_start < period[1]
            finish_in_period = period[0] < task.planned_finish <= period[1]
            if start_in_period:
                task.planned_start = period[1]
                task.planned_finish = self.calc_businesstimedelta(task.planned_start, task_duration)
                return task
            elif finish_in_period or \
                task.planned_start < period[0] and task.planned_finish > period[1]:
                task.interruption = self.calc_businesshrsdiff(period[0], period[1])
                return task
        return task

    def __get_task_duration__(self, task):
        """ get task duration in hours """
        task_duration = timedelta(0)
        if task.planned_start and task.planned_finish and task.planned_start < task.planned_finish:
            task_duration = self.calc_businesshrsdiff(task.planned_start, task.planned_finish)
        return task.subtask.duration if task_duration == timedelta(0) else task_duration

    def __queue_task__(self, task, last_task_finish):
        """ set planned start and finish """
        task_duration = self.__get_task_duration__(task)
        business_hour = businesstimedelta.BusinessTimeDelta(self.businesshrs, hours=1)
        task.planned_start = last_task_finish + business_hour - business_hour
        task.planned_start = task.planned_start.replace(tzinfo=None)
        task.planned_finish = self.calc_businesstimedelta(task.planned_start, task_duration)

        return self.__add_interruption__(task, task_duration)

    def planned_finish_with_interruption(self, task):
        """ return task planned finish with interruption taken into account """
        if task.planned_finish and task.interruption > timedelta(0):
            return self.calc_businesstimedelta(task.planned_finish, task.interruption)
        else:
            return task.planned_finish

    def __get_last_task_finish__(self):
        """ calculate last task finish time """
        last_task = self.employee.execution_set.filter(exec_status__in=[self.Done, self.OnCorrection, self.OnChecking],
                                                       task__exec_status__in=[self.InProgress, self.Done, self.Sent],
                                                       subtask__add_to_schedule=True
                                                       ) \
                                               .order_by('actual_finish').last()
        if last_task and last_task.actual_finish:
            return last_task.actual_finish
        return datetime.now().replace(hour=9,minute=0,second=0,microsecond=0)

    def recalc_queue(self):
        """ recalc queue for executors whem subtask changed"""

        tasks_to_do = self.employee.execution_set.filter(exec_status__in=[self.ToDo, self.InProgress],
                                                         subtask__add_to_schedule=True,
                                                         task__exec_status__in=[self.ToDo, self.InProgress]
                                                         )
        tasks_to_do_fixed = tasks_to_do.filter(fixed_date=True).values('planned_start', 'planned_finish')
        self.fixed_periods = self.__merge_fixed_periods__(tasks_to_do_fixed)
        self.tasks_to_do_not_fixed = tasks_to_do.filter(fixed_date=False) \
                                                .order_by('exec_status', F('planned_start').asc(nulls_last=True))

        execution_model = apps.get_model('planner.Execution')
        last_task_finish = self.__get_last_task_finish__()

        tasks = []
        # plan queued tasks
        for task in self.tasks_to_do_not_fixed:
            queued_task = self.__queue_task__(task, last_task_finish)
            tasks.append(queued_task)
            last_task_finish = self.planned_finish_with_interruption(queued_task)

        # perform bulk_update
        execution_model.objects.bulk_update(tasks, ['planned_start', 'planned_finish', 'interruption'])
