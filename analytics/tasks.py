""" Tasks for analytics app """
from datetime import datetime
from celery.utils.log import get_task_logger
from django.db.models import Q, Sum

from planner.celery import app
from planner.models import Employee, Task, IntTask
from analytics.models import Bonus

LOGGER = get_task_logger(__name__)


@app.task
def save_bonus():
    """ Save daily bonuses of Employees """
    employees = Employee.objects.all()

    for employee in employees:
        bonuses = 0

        # executor bonuses
        executions = employee.execution_set.filter(Q(task__exec_status=Task.Done) |
                                                   Q(task__exec_status=Task.Sent),
                                                   part__gt=0,
                                                   task__actual_finish__month=datetime.now().month,
                                                   task__actual_finish__year=datetime.now().year)
        for query in executions:
            bonuses += query.task.exec_bonus(query.part)

        # owner bonuses
        tasks = employee.task_set.filter(exec_status=Task.Sent,
                                         actual_finish__month=datetime.now().month,
                                         actual_finish__year=datetime.now().year)
        for query in tasks:
            bonuses += query.owner_bonus()

        # inttask bonuses
        inttask_bonus = employee.inttask_set.filter(exec_status=IntTask.Done,
                                                    actual_finish__month=datetime.now().month,
                                                    actual_finish__year=datetime.now().year)\
                                            .aggregate(Sum('bonus'))['bonus__sum']
        if inttask_bonus:
            bonuses += inttask_bonus

        # save bonuses
        bonus = Bonus(employee=employee, value=bonuses)
        bonus.save()

    LOGGER.info("Employee bonuses for %s saved", datetime.now())
