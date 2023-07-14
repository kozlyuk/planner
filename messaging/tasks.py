from datetime import date, timedelta
from smtplib import SMTPException
from celery.utils.log import get_task_logger
from django.utils.html import format_html
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.apps import apps

from planner.models import Employee, Deal, Task, Order
from html_templates.context import context_bonus_per_month
from planner.celery import app
from .context_email import context_actneed_deals, context_debtors_deals, \
                           context_overdue_tasks, context_payments


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

    template_name = "actneed_report.html"
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

    template_name = "debtors_report.html"
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

    template_name = "overdue_deals_report.html"
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

    template_name = "overdue_tasks_report.html"
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

    template_name = "unsent_tasks_report.html"
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

    template_name = "bonuses_report.html"
    employees = Employee.objects.exclude(user__is_staff=True,
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

    emails = []
    comment_model =apps.get_model('notice.Comment')
    comment = comment_model.objects.get(pk=comment_pk)

    if comment.content_type.model == 'task':
        template_name = "task_comment_email.html"
        try:
            task = Task.objects.get(pk=comment.object_id)
            recepients_set = set(task.executors.exclude(user__email='').values_list('user__email', flat=True))
            recepients_set.add(task.owner.user.email)
            recepients_set.update(list(Employee.objects.filter(user__is_superuser=True).values_list('user__email', flat=True)))
            recepients = list(recepients_set)

            # prepearing email
            context = {
                'employee': comment.user.employee.name,
                'task': task,
                'task_url': format_html('<a href="%s%s">%s</a>' %
                            (settings.SITE_URL, task.get_absolute_url(), task.object_code)),
                'comment': comment.text
            }
            subject = f'Додано коментар по проекту {task.object_code}'
            message = render_to_string(template_name, context)

        except Task.DoesNotExist:
            logger.info("Task with pk %s does not exists", comment.object_id)

    if comment.content_type.model == 'deal':
        template_name = "deal_comment_email.html"
        try:
            deal = Deal.objects.get(pk=comment.object_id)
            recepients = Employee.objects.filter(user__groups__name='Бухгалтери').values_list('user__email', flat=True)

            # prepearing email
            context = {
                'employee': comment.user.employee.name,
                'deal': deal,
                'deal_url': format_html('<a href="%s%s">%s</a>' %
                            (settings.SITE_URL, deal.get_absolute_url(), deal.number)),
                'comment': comment.text
            }
            subject = f'Додано коментар по договору {deal.number}'
            message = render_to_string(template_name, context)

        except Deal.DoesNotExist:
            logger.info("Deal with pk %s does not exists", comment.object_id)

    emails.append(EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recepients,
    ))

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails), ignore_holidays=True)


@app.task
def send_payment_notification(order_pk) -> None:
    """Sending notifications about new payment"""

    template_name = "payment_confirmed_email.html"

    try:
        order = Order.objects.get(pk=order_pk)
    except Order.DoesNotExist:
        logger.info("Task with pk %s does not exists", order_pk)

    recepients = set([order.company.accountant.user.email])
    recepients.update(Employee.objects.filter(user__is_superuser=True).values_list('user__email', flat=True))

    # prepearing email
    context = {
        'order': order,
        'order_url': format_html('<a href="%s%s">%s</a>' %
                     (settings.SITE_URL, order.get_absolute_url(), order)),
    }
    subject = f'Погоджено платіж {order}'
    message = render_to_string(template_name, context)

    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recepients,
    )

    # sending emails
    if email:
        send_email_list(change_content_type_to_html([email]), ignore_holidays=True)


@app.task
def send_payments_report() -> None:
    """Sending notifications about payments to accountants"""

    template_name = "payments_report.html"
    emails = []

    accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'],
                                          user__is_active=True,
                                          )

    for accountant in accountants:
        orders = Order.objects.filter(company__accountant=accountant,
                                      pay_status__in=[Order.Approved, Order.AdvanceApproved],
                                      pay_date__lte=date.today()+timedelta(days=7)
                                      ) \
                              .order_by('pay_date')
        if orders:
            recepients = set([accountant.user.email])
            recepients.update(list(Employee.objects.filter(user__is_superuser=True).values_list('user__email', flat=True)))

            # prepearing email
            context = context_payments(orders, accountant)
            subject = f'Платежі на {date.today()}'
            message = render_to_string(template_name, context)

            emails.append(EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recepients
            ))
        else:
            continue

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails), ignore_holidays=True)


@app.task
def send_payments_approval_report() -> None:
    """Sending notifications about payments to managers """

    template_name = "approval_report.html"
    emails = []

    managers = Employee.objects.filter(user__is_superuser=True)

    for manager in managers:
        orders = Order.objects.filter(pay_status__in=[Order.NotPaid,Order.AdvancePaid],
                                      pay_date__lte=date.today()+timedelta(days=7)
                                      ) \
                              .order_by('pay_date')
        if orders:
            recepients = [manager.user.email]

            # prepearing email
            context = context_payments(orders, manager)
            subject = f'Погодження платежів на {date.today()}'
            message = render_to_string(template_name, context)

            emails.append(EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recepients
            ))
        else:
            continue

    # sending emails
    if emails:
        send_email_list(change_content_type_to_html(emails), ignore_holidays=True)
