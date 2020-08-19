from datetime import date, timedelta
from smtplib import SMTPException
from dateutil.relativedelta import relativedelta
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.conf.locale.uk import formats as uk_formats
from django.template.loader import render_to_string

from planner.models import Employee, Deal, Task
from planner.celery import app
from planner.context import context_bonus_per_month
from planner.context_email import context_actneed_deals, context_debtors_deals, \
                                  context_overdue_tasks

date_format = uk_formats.DATE_INPUT_FORMATS[0]
logger = get_task_logger(__name__)


@app.task
def update_task_statuses(task_id=None):
    """ Update statuses. If task_id given updates for task_id else updates for last 500 tasks """
    if task_id:
        tasks = Task.objects.filter(pk=task_id)
    else:
        tasks = Task.objects.order_by('-id')[:500]
    for task in tasks:
        sending_status = task.sending_status()
        if task.manual_warning:
            warning = task.manual_warning
        elif task.exec_status == Task.OnHold:
            warning = 'Призупинено'
        elif task.exec_status == Task.Canceled:
            warning = 'Відмінено'
        elif task.exec_status == Task.Done and sending_status != 'Надіслано':
            warning = sending_status
        elif task.exec_status in [Task.Sent, Task.Done] and task.actual_finish:
            warning = 'Виконано %s' % task.actual_finish.strftime(date_format)
        elif task.execution_status() == 'Виконано':
            warning = 'Очікує на перевірку'
        elif task.planned_finish:
            if task.planned_finish < date.today():
                warning = 'Протерміновано %s' % task.planned_finish.strftime(
                    date_format)
            elif task.planned_finish - timedelta(days=7) <= date.today():
                warning = 'Завершується %s' % task.planned_finish.strftime(
                    date_format)
            else:
                warning = 'Завершити до %s' % task.planned_finish.strftime(
                    date_format)
        elif task.deal.expire_date < date.today():
            warning = 'Протерміновано %s' % task.deal.expire_date.strftime(
                date_format)
        elif task.deal.expire_date - timedelta(days=7) <= date.today():
            warning = 'Завершується %s' % task.deal.expire_date.strftime(
                date_format)
        else:
            warning = 'Завершити до %s' % task.deal.expire_date.strftime(
                date_format)

        Task.objects.filter(id=task.id).update(warning=warning)

    logger.info("Updated task %s warnings", task_id)


@app.task
def update_deal_statuses(deal_id=None):
    """ Update statuses and warnings. If deal_id given updates for deal_id else updates for last 200 deals """
    if deal_id:
        deals = Deal.objects.filter(pk=deal_id)
    else:
        deals = Deal.objects.order_by('-id')[:200]
    for deal in deals:
        tasks = deal.task_set.values_list('exec_status', flat=True)
        if Task.ToDo in tasks:
            exec_status = Deal.ToDo
        elif Task.InProgress in tasks:
            exec_status = Deal.InProgress
        elif Task.Done in tasks:
            exec_status = Deal.Done
        else:
            exec_status = Deal.Sent

        if deal.manual_warning:
            warning = deal.manual_warning
        elif deal.task_set.all().count() == 0:
            warning = 'Відсутні проекти'
        elif exec_status == Deal.Sent:
            value_calc = deal.value_calc() + deal.value_correction
            if deal.value > 0 and deal.value != value_calc:
                warning = 'Вартість по роботам %s' % value_calc
            elif deal.act_status == deal.NotIssued or deal.act_status == deal.PartlyIssued:
                warning = 'Очікує закриття акту'
            elif deal.pay_status != deal.PaidUp and deal.pay_date:
                warning = 'Оплата %s' % deal.pay_date.strftime(date_format)
            else:
                warning = ''
        elif deal.expire_date < date.today():
            warning = 'Протерміновано %s' % deal.expire_date.strftime(
                date_format)
        elif deal.expire_date - timedelta(days=7) <= date.today():
            warning = 'Закінчується %s' % deal.expire_date.strftime(
                date_format)
        else:
            warning = ''

        Deal.objects.filter(id=deal.id).update(
            exec_status=exec_status, warning=warning)

    logger.info("Updated deal %s statuses and warnings", deal_id)


def send_email_list(emails: EmailMessage) -> None:
    """ sends email to emails list """
    try:
        connection = get_connection()
        connection.open()
        message_count = connection.send_messages(emails)
        connection.close()
        logger.info("Sent %s messages", message_count)
        print(f"Sent { message_count} messages")
    except SMTPException as error:
        logger.warning("Connection error while sending emails: %s", error)


def change_content_type_to_html(emails: EmailMessage) -> EmailMessage:
    """ changing content_type to html """
    for email in emails:
        email.content_subtype = "html"
    return emails


@app.task
def send_actneed_report():
    """Sending notifications about closed contracts to accountants"""

    template_name = "email/actneed_report.html"
    accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.filter(exec_status=Deal.Sent)\
                        .exclude(act_status=Deal.Issued)\
                        .exclude(number__icontains='загальний')

    # prepearing emails
    emails = []
    for employee in accountants:
        context = context_actneed_deals(deals, employee)
        if deals and employee.user.email:
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Угоди які чекають закриття акту',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
            ))

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))


@app.task
def send_debtors_report():
    """Sending notifications about debtors to accountants"""

    template_name = "email/debtors_report.html"
    accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.filter(exec_status=Deal.Sent)\
                        .exclude(pay_status=Deal.PaidUp) \
                        .exclude(pay_date__isnull=True) \
                        .exclude(pay_date__gte=date.today()) \
                        .exclude(number__icontains='загальний')
    # prepearing emails
    emails = []
    for employee in accountants:
        context = context_debtors_deals(deals, employee)
        if deals and employee.user.email:
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Угоди в яких пройшов термін оплати',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
            ))
    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))


@app.task
def send_overdue_deals_report():
    """Sending notifications about overdue deals to PMs"""

    template_name = "email/overdue_deals_report.html"
    project_managers = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.exclude(exec_status=Deal.Sent)\
                        .exclude(expire_date__gte=date.today()) \
                        .exclude(number__icontains='загальний') \
                        .exclude(number__icontains='злетіли')
    # prepearing emails
    emails = []
    for employee in project_managers:
        context = context_debtors_deals(deals, employee)
        if deals and employee.user.email:
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Протерміновані угоди',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
            ))
    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))


@app.task
def send_overdue_tasks_report():
    """Sending notifications about overdue tasks to owners and executors"""

    template_name = "email/overdue_tasks_report.html"
    employees = Employee.objects.filter(user__is_active=True)

    # prepearing emails
    emails = []
    for employee in employees:
        context = context_overdue_tasks(employee)
        if employee.user.email and (context['tasks'] \
                or context['executions'] or context['inttasks']):
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Протерміновані роботи',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua'],
                ))

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))


@app.task
def send_unsent_tasks_report():
    """Sending notifications about unsent tasks to owners"""

    template_name = "email/unsent_tasks_report.html"
    project_managers = Employee.objects.filter(user__groups__name__in=['ГІПи'])

    # prepearing emails
    emails = []
    for employee in project_managers:
        context = context_overdue_tasks(employee)
        if employee.user.email and context['tasks']:
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Не надіслані проекти',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua'],
                ))

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))


@app.task
def send_monthly_report(period=None):
    """ Sending monthly report to employee """

    template_name = "email/bonuses_report.html"
    employees = Employee.objects.exclude(user__username__startswith='outsourcing')

    # if period is None set previous month
    if not period:
        period = date.today() - relativedelta(months=1)

    # prepearing emails
    emails = []
    for employee in employees:
        context = context_bonus_per_month(employee, period)
        if employee.user.email and (context['tasks'] \
                or context['executions'] or context['inttasks']):
            message = render_to_string(template_name, context)
            emails.append(EmailMessage(
                'Бонуси за виконання проектів {}.{}'.format(period.month, period.year),
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua'],
                ))

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails))
