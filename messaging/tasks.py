from datetime import date
from smtplib import SMTPException
from celery.utils.log import get_task_logger
from django.utils.html import format_html
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.apps import apps

from planner.models import Employee, Deal, Task
from html_templates.context import context_bonus_per_month
from planner.celery import app
from .context_email import context_actneed_deals, context_debtors_deals, \
                           context_overdue_tasks


logger = get_task_logger(__name__)


def public_holiday() -> bool:
    """ check if today is public holiday """
    event =apps.get_model('notice.Event')
    return event.objects.filter(next_date=date.today(), is_holiday=True).exists()


@app.task
def send_email_list(emails: EmailMessage, ignore_holidays = False) -> None:
    """ sends email to emails list """

    if not ignore_holidays and public_holiday():
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
        print(error)


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
    deals = Deal.objects.waiting_for_act()

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
    deals = Deal.objects.overdue_execution()

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


@app.task
def send_comment_notification(comment_pk) -> None:
    """Sending notifications about new comment"""

    template_name = "email/comment_email.html"
    emails = []
    comment_model =apps.get_model('notice.Comment')
    comment = comment_model.objects.get(pk=comment_pk)

    try:
        task = Task.objects.get(pk=comment.object_id)
        recepients_set = set(task.executors.exclude(user__email='').values_list('user__email', flat=True))
        recepients_set.add(task.owner.user.email)
        recepients_set.update(list(Employee.objects.filter(user__is_superuser=True).values_list('user__email', flat=True)))

        # prepearing email
        context = {
            'employee': comment.user.employee.name,
            'task': task,
            'task_url': format_html('<a href="%s%s">%s</a>' %
                        (settings.SITE_URL, task.get_absolute_url(), task.object_code)),
            'comment': comment.text
        }
        message = render_to_string(template_name, context)

        emails.append(EmailMessage(
            f'Додано коментар по {task.object_code}',
            message,
            settings.DEFAULT_FROM_EMAIL,
            list(recepients_set),
        ))

        # sending emails
        if emails:
            send_email_list(change_content_type_to_html(emails), ignore_holidays=True)

    except Task.DoesNotExist:
        logger.info("Task with pk %s does not exists", comment.object_id)
