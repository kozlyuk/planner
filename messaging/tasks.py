from datetime import date
from smtplib import SMTPException
from celery.utils.log import get_task_logger
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string

from notice.models import Event
from planner.models import Employee, Deal
from html_templates.context import context_bonus_per_month
from planner.celery import app
from .context_email import context_actneed_deals, context_debtors_deals, \
                           context_overdue_tasks


logger = get_task_logger(__name__)


def public_holiday() -> bool:
    """ check if today is public holiday """
    return Event.objects.filter(next_date=date.today()).exists()


@app.task
def send_email_list(emails: EmailMessage) -> None:
    """ sends email to emails list """

    if public_holiday():
        print(f"Innore sending due to public holiday")
        return

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
    accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'],
                                          user__is_active=True,
                                          )
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
    accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'],
                                          user__is_active=True,
                                          )
    deals = Deal.objects.overdue_payment()

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
    project_managers = Employee.objects.filter(user__groups__name__in=['Бухгалтери'],
                                               user__is_active=True,
                                               )
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
    project_managers = Employee.objects.filter(user__groups__name__in=['ГІПи'],
                                               user__is_active=True,
                                               )

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
    employees = Employee.objects.exclude(user__username__startswith='outsourcing',
                                         user__is_active=True,
                                         )

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
