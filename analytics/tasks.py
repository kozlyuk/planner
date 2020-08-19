""" Tasks for analytics app """
from datetime import date
from decimal import Decimal
from celery.utils.log import get_task_logger
from django.db.models import Sum

from planner.celery import app
from planner.models import Employee, Execution
from analytics.models import Kpi

LOGGER = get_task_logger(__name__)


@app.task
def calc_bonuses(month=date.today().month, year=date.today().year):
    """ Save monthly bonuses of Employees """
    employees = Employee.objects.filter(user__is_active=True)
    period = date(year=year, month=month, day=1)

    for employee in employees:

        for kpi_name in [(1, Kpi.BonusItel), (2, Kpi.BonusGKP), (3, Kpi.BonusSIA)]:
            bonuses = 0

            # calculate executor bonuses
            executions = employee.execution_set.filter(task__deal__company=kpi_name[0],
                                                       exec_status=Execution.Done,
                                                       finish_date__month=month,
                                                       finish_date__year=year)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate owner bonuses
            tasks = employee.task_set.filter(deal__company=kpi_name[0],
                                             sending_date__month=month,
                                             sending_date__year=year)
            for query in tasks:
                bonuses += query.owner_bonus()

            # save bonuses
            if bonuses > 0:
                kpi, created = Kpi.objects.get_or_create(employee=employee,
                                                         name=kpi_name[1],
                                                         period__month=month,
                                                         period__year=year)
                kpi.value = bonuses
                kpi.period = period
                kpi.save()

        # calculate inttask bonuses
        inttask_bonus = employee.inttask_set.filter(actual_finish__month=month,
                                                    actual_finish__year=year)\
                                            .aggregate(Sum('bonus'))['bonus__sum']

        # save inttasks bonuses
        if inttask_bonus:
            kpi, created = Kpi.objects.get_or_create(employee=employee,
                                                     name=Kpi.Tasks,
                                                     period__month=month,
                                                     period__year=year)
            kpi.value = inttask_bonus
            kpi.period = period
            kpi.save()

    LOGGER.info("Employee bonuses for %s.%s saved", month, year)


@app.task
def calc_kpi(month=date.today().month, year=date.today().year):
    """ Save monthly bonuses of Employees """
    employees = Employee.objects.filter(user__is_active=True)
    period = date(year=year, month=month, day=1)

    for employee in employees:

        # calculate productivity for PMs
        if employee.user.groups.filter(name='ГІПи').exists():

            # calculate owner`s team income
            income = Decimal(0)
            tasks = employee.task_set.filter(actual_finish__month=month,
                                             actual_finish__year=year)
            for task in tasks:
                income += task.project_type.net_price()

            # calculate owner`s team salaries
            salaries = employee.salary
            team_members = employee.employee_set.filter(user__is_active=True)
            for member in team_members:
                salaries += member.salary

            if salaries > 0:
                # calculate owner`s productivity
                if month == date.today().month and year == date.today().year:
                    # productivity for current month
                    # 3000 = 30(days in month) * 100(percentage)
                    productivity = income / salaries / employee.coefficient / date.today().day * 3000
                else:
                    # productivity for previous month
                    # 3000 = 30(days in month) * 100(percentage)
                    productivity = income / salaries / employee.coefficient * 100

        # calculate productivity for executors
        elif employee.user.groups.filter(name='Проектувальники').exists():
            # calculate executor bonuses
            bonuses = 0
            executions = employee.execution_set.filter(finish_date__month=month,
                                                       finish_date__year=year)
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate inttask bonuses
            inttask_bonus = employee.inttask_set.filter(actual_finish__month=month,
                                                        actual_finish__year=year) \
                                                .aggregate(Sum('bonus'))['bonus__sum']
            if inttask_bonus:
                bonuses += inttask_bonus

            if employee.salary > 0:
                # calculate productivity
                if month == date.today().month and year == date.today().year:
                    # productivity for current month
                    # 300000 = 30(days in month) * 100(percentage) * 100(percentage)
                    productivity = bonuses / employee.salary / employee.coefficient / date.today().day * 300000
                else:
                    # productivity for previous month
                    # 10000 = 100(percentage) * 100(percentage)
                    productivity = bonuses / employee.salary / employee.coefficient * 10000


        # save productivity
        if productivity:
            kpi, created = Kpi.objects.get_or_create(employee=employee,
                                                     name=Kpi.Productivity,
                                                     period__month=month,
                                                     period__year=year)
            kpi.value = productivity
            kpi.period = period
            kpi.save()

    LOGGER.info("Employee KPIs for %s.%s saved", month, year)
