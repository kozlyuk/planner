""" Tasks for analytics app """
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from celery.utils.log import get_task_logger
from django.db.models import Sum
from weasyprint import HTML, CSS

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
            executions = employee.executions_for_period(period).filter(task__deal__company=kpi_name[0])
            for query in executions:
                bonuses += query.task.exec_bonus(query.part)

            # calculate owner bonuses
            tasks = employee.tasks_for_period(period).filter(deal__company=kpi_name[0])
            for query in tasks:
                bonuses += query.owner_bonus()

            # save bonuses
            if bonuses > 0:
                Kpi.objects.create(employee=employee,
                                   name=kpi_name[1],
                                   value=bonuses,
                                   period=period
                                   )

        # calculate inttask bonuses
        inttask_bonus = employee.inttask_set.filter(actual_finish__month=period.month,
                                                    actual_finish__year=period.year)\
                                            .aggregate(Sum('bonus'))['bonus__sum']

        # save inttasks bonuses
        if inttask_bonus:
            Kpi.objects.create(employee=employee,
                               name=Kpi.Tasks,
                               value=inttask_bonus,
                               period=period
                               )

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
        bonus = Kpi.objects.filter(employee=employee,
                                   name__in=[Kpi.BonusItel, Kpi.BonusGKP, Kpi.Tasks],
                                   period__month=period.month,
                                   period__year=period.year)\
                           .aggregate(Sum('value'))['value__sum'] or 0

        if employee.salary > 0:
            # calculate productivity
            # 10000 = 100(percentage) * 100(percentage)
            productivity = bonus / employee.salary / employee.coefficient * 10000

        # save productivity
        if productivity:
            Kpi.objects.create(employee=employee,
                               name=Kpi.Productivity,
                               value=productivity,
                               period=period
                               )

    LOGGER.info("Employee KPIs for %s.%s saved", period.month, period.year)


@app.task
def recalc_kpi(prev_month=False, period=None):
    """ Clear existing KPIs and generate new """
    Kpi.objects.filter(period=period).delete()
    calc_bonuses(prev_month, period)
    calc_kpi(prev_month, period)


@app.task
def generate_pdf(template, context):
    """ Generate pdf file of template """

    rendered_html = template.render(context)
    pdf_file = HTML(string=rendered_html).write_pdf()

    return pdf_file
