""" Tasks for analytics app """
from datetime import date
from celery.utils.log import get_task_logger
from django.db.models import Sum

from planner.celery import app
from planner.models import Employee
from analytics.models import Kpi

LOGGER = get_task_logger(__name__)


@app.task
def save_kpi(month=date.today().month, year=date.today().year):
    """ Save monthly bonuses of Employees """
    employees = Employee.objects.all()
    period = date(year=year, month=month, day=1)

    for employee in employees:

        for kpi_name in [(1, Kpi.BonusItel), (2, Kpi.BonusGKP)]:
            bonuses = 0

            # executor bonuses
            executions = employee.execution_set.filter(task__deal__customer=kpi_name[0],
                                                       task__actual_finish__month=month,
                                                       task__actual_finish__year=year)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # owner bonuses
            tasks = employee.task_set.filter(deal__customer=kpi_name[0],
                                             actual_finish__month=month,
                                             actual_finish__year=year
                                             )
            for query in tasks:
                bonuses += query.owner_bonus()

            # save bonuses
            if bonuses > 0:
                Kpi.objects.get_or_create(employee=employee,
                                          name=kpi_name[1],
                                          period__month=month,
                                          period__year=year,
                                          defaults={'value': bonuses,
                                          'period': period}
                                          )

        # inttask bonuses
        inttask_bonus = employee.inttask_set.filter(actual_finish__month=month,
                                                    actual_finish__year=year)\
                                            .aggregate(Sum('bonus'))['bonus__sum']
        if inttask_bonus:
            bonuses += inttask_bonus

        # save inttasks bonuses
        if bonuses > 0:
            Kpi.objects.get_or_create(employee=employee,
                                      name=Kpi.Tasks,
                                      period__month=month,
                                      period__year=year,
                                      defaults={'value': bonuses,
                                     'period': period}
                                      )

        # save productivity
        if employee.salary > 0:
            productivity = bonuses / employee.salary / employee.coefficient * 100

            if bonuses > 0:
                Kpi.objects.get_or_create(employee=employee,
                                          name=Kpi.Productivity,
                                          period__month=month,
                                          period__year=year,
                                          defaults={'value': productivity,
                                          'period': period}
                                          )

    LOGGER.info("Employee bonuses for %s.%s saved", month, year)
