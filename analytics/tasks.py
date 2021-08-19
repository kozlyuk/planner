""" Tasks for analytics app """
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from celery.utils.log import get_task_logger
from django.db.models import Sum

from planner.celery import app
from planner.models import Employee, Execution
from analytics.models import Kpi

LOGGER = get_task_logger(__name__)


@app.task
def calc_bonuses(prev_month=False, period=None):
    """ Save monthly bonuses of Employees """
    employees = Employee.objects.filter(user__is_active=True)
    if not period:
        period = date.today()
    if prev_month:
        period = period - relativedelta(months=1)
    period = period.replace(day=1)

    for employee in employees:
        for kpi_name in [(1, Kpi.BonusItel), (2, Kpi.BonusGKP), (3, Kpi.BonusSIA)]:
            bonuses = 0

            # calculate executor bonuses
            executions = employee.execution_set.filter(task__deal__company=kpi_name[0],
                                                       exec_status=Execution.Done,
                                                       finish_date__month=period.month,
                                                       finish_date__year=period.year)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate owner bonuses
            tasks = employee.task_set.filter(deal__company=kpi_name[0],
                                             sending_date__month=period.month,
                                             sending_date__year=period.year)
            for query in tasks:
                bonuses += query.owner_bonus()

            # save bonuses
            if bonuses > 0:
                kpi, _ = Kpi.objects.get_or_create(employee=employee,
                                                   name=kpi_name[1],
                                                   period__month=period.month,
                                                   period__year=period.year)
                kpi.value = bonuses
                kpi.period = period
                kpi.save()

        # calculate inttask bonuses
        inttask_bonus = employee.inttask_set.filter(actual_finish__month=period.month,
                                                    actual_finish__year=period.year)\
                                            .aggregate(Sum('bonus'))['bonus__sum']

        # save inttasks bonuses
        if inttask_bonus:
            kpi, _ = Kpi.objects.get_or_create(employee=employee,
                                               name=Kpi.Tasks,
                                               period__month=period.month,
                                               period__year=period.year)
            kpi.value = inttask_bonus
            kpi.period = period
            kpi.save()

    LOGGER.info("Employee bonuses for %s.%s saved", period.month, period.year)


@app.task
def calc_kpi(prev_month=False, period=None):
    """ Save monthly bonuses of Employees """
    employees = Employee.objects.filter(user__is_active=True, user__groups__name='Проектувальники')
    if not period:
        period = date.today()
    if prev_month:
        period = period - relativedelta(months=1)
    period = period.replace(day=1)

    for employee in employees:
        # calculate productivity for PMs
        if employee.user.groups.filter(name='ГІПи').exists():

            # calculate owner`s team income
            income = Decimal(0)
            tasks = employee.task_set.filter(actual_finish__month=period.month,
                                             actual_finish__year=period.year)
            for task in tasks:
                income += task.project_type.net_price()

            # calculate owner`s team salaries
            salaries = employee.salary
            team_members = employee.employee_set.filter(user__is_active=True)
            for member in team_members:
                salaries += member.salary

            if salaries > 0:
                # calculate owner`s productivity
                if period.month == date.today().month and period.year == date.today().year:
                    # productivity for current month
                    # 3000 = 30(days in month) * 100(percentage)
                    productivity = income / salaries / employee.coefficient / date.today().day * 3000
                else:
                    # productivity for previous month
                    # 3000 = 30(days in month) * 100(percentage)
                    productivity = income / salaries / employee.coefficient * 100

        # calculate productivity for executors
        elif employee.user.groups.filter(name='Проектувальники').exists():
            # calculate executor bonuses for Done subtasks
            bonuses = 0
            executions = employee.execution_set.filter(finish_date__month=period.month,
                                                       finish_date__year=period.year)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate executor bonuses for OnChecking subtasks
            executions = employee.execution_set.filter(exec_status=Execution.OnChecking)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate inttask bonuses
            inttask_bonus = employee.inttask_set.filter(actual_finish__month=period.month,
                                                        actual_finish__year=period.year) \
                                                .aggregate(Sum('bonus'))['bonus__sum']
            if inttask_bonus:
                bonuses += inttask_bonus

            if employee.salary > 0:
                # calculate productivity
                if period.month == date.today().month and period.year == date.today().year:
                    # productivity for current month
                    # 300000 = 30(days in month) * 100(percentage) * 100(percentage)
                    productivity = bonuses / employee.salary / employee.coefficient / date.today().day * 300000
                else:
                    # productivity for previous month
                    # 10000 = 100(percentage) * 100(percentage)
                    productivity = bonuses / employee.salary / employee.coefficient * 10000


        # save productivity
        if productivity:
            kpi, _ = Kpi.objects.get_or_create(employee=employee,
                                               name=Kpi.Productivity,
                                               period__month=period.month,
                                               period__year=period.year)
            kpi.value = productivity
            kpi.period = period
            kpi.save()

    LOGGER.info("Employee KPIs for %s.%s saved", period.month, period.year)
