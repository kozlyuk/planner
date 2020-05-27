from planner.celery import app
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core import mail
from datetime import date, timedelta
from django.conf.locale.uk import formats as uk_formats
from django.db.models import Q
from planner.models import Employee, Deal, Task, Execution, IntTask, Event

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

    logger.info("Updated task {} warnings".format(task_id))


@app.task
def update_deal_statuses(deal_id=None):
    """ Update statuses and warnings. If deal_id given updates for deal_id else updates for last 100 deals """
    if deal_id:
        deals = Deal.objects.filter(pk=deal_id)
    else:
        deals = Deal.objects.order_by('-id')[:100]
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

    logger.info("Updated deal {} statuses and warnings".format(deal_id))


@app.task
def event_next_date_calculate():
    """Calculate next_date fields for Events"""
    for event in Event.objects.all():
        event.next_date = event.next_repeat()
        event.save(update_fields=['next_date'], logging=False)
    logger.info("Calculated next_date fields for Events")


@app.task
def send_actneed_report():
    """Sending notifications about closed contracts to accountants"""

    accountants = Employee.objects.filter(
        user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.filter(exec_status=Deal.Sent)\
                        .exclude(act_status=Deal.Issued)\
                        .exclude(number__icontains='загальний')
    emails = []

    for accountant in accountants:

        if deals and accountant.user.email:
            index = 0
            message = '<html><body>\
                       Шановна(ий) {}.<br><br>\
                       Є виконані угоди які чекають закриття акту виконаних робіт:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Номер договору</th><th>Замовник</th>\
                       <th>Вартість робіт</th><th>Статус оплати</th><th>Акт виконаних робіт</th>' \
                .format(accountant.user.first_name)

            for deal in deals:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/deal/{}/change/">{}</a></td>\
                           <td>{}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, deal.pk, deal.number, deal.customer,
                            deal.value, deal.get_pay_status_display(), deal.get_act_status_display())

            message += '</table></body></html><br>'

            emails.append(mail.EmailMessage(
                'Угоди які чекають закриття акту',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [accountant.user.email],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info("Sent notifications about closed contracts to accountants")
    connection.close()


@app.task
def send_debtors_report():
    """Sending notifications about debtors to accountants"""

    accountants = Employee.objects.filter(
        user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.filter(exec_status=Deal.Sent)\
                        .exclude(pay_status=Deal.PaidUp) \
                        .exclude(pay_date__isnull=True) \
                        .exclude(pay_date__gte=date.today()) \
                        .exclude(number__icontains='загальний')
    emails = []

    for accountant in accountants:

        if deals and accountant.user.email:
            index = 0
            message = '<html><body>\
                       Шановна(ий) {}.<br><br>\
                       В наступних угодах пройшов термін оплати:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Номер договору</th><th>Замовник</th>\
                       <th>Вартість робіт</th><th>Статус оплати</th>\
                       <th>Акт виконаних робіт</th><th>Статус виконання</th>' \
                .format(accountant.user.first_name)

            for deal in deals:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/deal/{}/change/">{}</a></td>\
                           <td>{}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{!s}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, deal.pk, deal.number, deal.customer,
                            deal.value, deal.get_pay_status_display(),
                            deal.get_act_status_display(), deal.get_exec_status_display())

            message += '</table></body></html><br>'

            emails.append(mail.EmailMessage(
                'Угоди в яких пройшов термін оплати',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [accountant.user.email],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info("Sent notifications about debtors to accountants")
    connection.close()


@app.task
def send_overdue_deals_report():
    """Sending notifications about overdue deals to PMs"""

    pms = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
    deals = Deal.objects.exclude(exec_status=Deal.Sent)\
                        .exclude(expire_date__gte=date.today()) \
                        .exclude(number__icontains='загальний') \
                        .exclude(number__icontains='злетіли')
    emails = []

    for pm in pms:

        if deals and pm.user.email:
            index = 0
            message = '<html><body>\
                               Шановна(ий) {}.<br><br>\
                               Маємо такі протерміновані угоди:<br>\
                               <table border="1">\
                               <th>&#8470;</th><th>Номер договору</th><th>Замовник</th>\
                               <th>Вартість робіт</th><th>Статус оплати</th>\
                               <th>Акт виконаних робіт</th><th>Дата закінчення договору</th>\
                               <th>Статус виконання</th>' \
                .format(pm.user.first_name)

            for deal in deals:
                index += 1
                message += '<tr>\
                                   <td>{}</td>\
                                   <td><a href="http://erp.itel.rv.ua/deal/{}/change/">{}</a></td>\
                                   <td>{}</td>\
                                   <td>{}</td>\
                                   <td>{!s}</td>\
                                   <td>{!s}</td>\
                                   <td>{!s}</td>\
                                   <td>{}</td>\
                                   </tr>' \
                    .format(index, deal.pk, deal.number, deal.customer,
                            deal.value, deal.get_pay_status_display(),
                            deal.get_act_status_display(), deal.expire_date,
                            deal.get_exec_status_display())

            message += '</table></body></html><br>'

            emails.append(mail.EmailMessage(
                'Протерміновані угоди',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [pm.user.email],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info("Sent notifications about overdue deals to PMs")
    connection.close()


@app.task
def send_overdue_tasks_report():
    """Sending notifications about overdue tasks to owners and executors"""

    employees = Employee.objects.filter(user__is_active=True)
    tasks = Task.objects.exclude(exec_status=Task.Sent) \
                        .exclude(exec_status=Task.Done) \
                        .exclude(deal__expire_date__gte=date.today(),
                                 planned_finish__isnull=True) \
                        .exclude(deal__expire_date__gte=date.today(),
                                 planned_finish__gte=date.today())
    inttasks = IntTask.objects.exclude(exec_status=IntTask.Done) \
                              .exclude(planned_finish__gte=date.today())

    emails = []

    for employee in employees:
        otasks = tasks.filter(owner=employee)
        etasks = tasks.filter(executors=employee)
        einttasks = inttasks.filter(executor=employee)

        message = '<html><body>Шановний(а) {}.<br><br>' \
            .format(employee.user.first_name)

        if otasks.exists():
            index = 0
            message += 'Протерміновані наступні проекти, в яких Ви відповідальна особа:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Статус</th><th>Планове закінчення</th><th>Попередження</th>'

            for task in otasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="https://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                           <td>{:.80}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           </tr>'. \
                    format(index, task.pk, task.object_code, task.object_address,
                           task.project_type, task.get_exec_status_display(),
                           task.planned_finish, task.warning)

            message += '</table><br>'

        if etasks.exists():
            index = 0
            message += 'Протерміновані наступні проекти, в яких Ви виконуєте роботи:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Статус</th><th>Планове закінчення</th><th>Попередження</th>'

            for task in etasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="https://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                           <td>{:.80}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, task.pk, task.object_code, task.object_address,
                            task.project_type, task.get_exec_status_display(),
                            task.planned_finish, task.warning)

            message += '</table></body></html><br>'

        if einttasks.exists():
            index = 0
            message += 'Ви протермінували наступні завдання:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Завдання</th><th>Статус</th><th>Планове закінчення</th>'

            for task in einttasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="https://erp.itel.rv.ua/inttask/{}/">{}</a></td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           </tr>' \
                    .format(index, task.pk, task.task_name, task.get_exec_status_display(),
                            task.planned_finish)
            message += '</table></body></html><br>'

        if otasks.exists() or etasks.exists() or einttasks.exists():
            emails.append(mail.EmailMessage(
                'Протерміновані проекти',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua', 'm.kozlyuk@itel.rv.ua'],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info(
            "Sent notifications about overdue tasks to owners and executors")
    connection.close()


@app.task
def send_urgent_tasks_report():
    """Sending notifications about urgent tasks to owners and executors"""

    employees = Employee.objects.filter(user__is_active=True)
    tasks = Task.objects.exclude(exec_status=Task.Sent) \
                        .exclude(exec_status=Task.Done) \
                        .exclude(planned_finish__isnull=True,
                                 deal__expire_date__lt=date.today()) \
                        .exclude(planned_finish__isnull=True,
                                 deal__expire_date__gt=date.today() + timedelta(days=7)) \
                        .exclude(planned_finish__lt=date.today()) \
                        .exclude(planned_finish__gt=date.today() + timedelta(days=7))
    inttasks = IntTask.objects.exclude(exec_status=IntTask.Done) \
                              .exclude(planned_finish__lt=date.today()) \
                              .exclude(planned_finish__gt=date.today() + timedelta(days=7))

    emails = []

    for employee in employees:
        otasks = tasks.filter(owner=employee)
        etasks = tasks.filter(executors=employee)
        einttasks = inttasks.filter(executor=employee)

        message = '<html><body>Шановний(а) {}.<br><br>' \
            .format(employee.user.first_name)

        if otasks.exists():
            index = 0
            message += 'Завершується термін виконання наступних проектів, в яких Ви відповідальна особа:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Статус</th><th>Планове закінчення</th><th>Попередження</th>'

            for task in otasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                           <td>{:.80}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, task.pk, task.object_code, task.object_address,
                            task.project_type, task.get_exec_status_display(),
                            task.planned_finish, task.warning)
            message += '</table><br>'

        if etasks.exists():
            index = 0
            message += 'Завершується термін виконання наступних проектів, в яких Ви виконуєте роботи:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Статус</th><th>Планове закінчення</th><th>Попередження</th>'

            for task in etasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                           <td>{:.80}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, task.pk, task.object_code, task.object_address,
                            task.project_type, task.get_exec_status_display(),
                            task.planned_finish, task.warning)
            message += '</table></body></html><br>'

        if einttasks.exists():
            index = 0
            message += 'Завершується термін виконання наступних завдань:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Завдання</th><th>Статус</th><th>Планове закінчення</th>'

            for task in einttasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/inttask/{}/">{}</a></td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           </tr>' \
                    .format(index, task.pk, task.task_name, task.get_exec_status_display(),
                            task.planned_finish)
            message += '</table></body></html><br>'

        if otasks.exists() or etasks.exists() or einttasks.exists():
            emails.append(mail.EmailMessage(
                'Завершується термін виконання проектів',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua', 'm.kozlyuk@itel.rv.ua'],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info(
            "Sent notifications about urgent tasks to owners and executors")
    connection.close()


@app.task
def send_unsent_tasks_report():
    """Sending notifications about unsent tasks to owners"""

    pms = Employee.objects.filter(user__groups__name__in=['ГІПи'])
    tasks = Task.objects.filter(exec_status=Task.Done)

    emails = []

    for employee in pms:
        otasks = tasks.filter(owner=employee)

        message = '<html><body>Шановний(а) {}.<br><br>' \
            .format(employee.user.first_name)

        if otasks.exists():
            index = 0
            message += 'Не надіслані наступні проекти, в яких Ви відповідальна особа:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Статус</th><th>Планове закінчення</th><th>Попередження</th>'

            for task in otasks:
                index += 1
                message += '<tr>\
                           <td>{}</td>\
                           <td><a href="http://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                           <td>{:.80}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           <td>{}</td>\
                           <td>{!s}</td>\
                           </tr>' \
                    .format(index, task.pk, task.object_code, task.object_address,
                            task.project_type, task.get_exec_status_display(),
                            task.planned_finish, task.warning)
            message += '</table><br>'

            emails.append(mail.EmailMessage(
                'Не надіслані проекти',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [employee.user.email],
                ['s.kozlyuk@itel.rv.ua', 'm.kozlyuk@itel.rv.ua'],
            ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info("Sent notifications about unsent tasks to owners")
    connection.close()


@app.task
def send_monthly_report():
    """Sending monthly report to employee"""

    month = date.today().month - 1
    year = date.today().year

    employees = Employee.objects.exclude(
        user__username__startswith='outsourcing')
    tasks = Task.objects.filter(exec_status=Task.Sent,
                                actual_finish__month=month,
                                actual_finish__year=year)
    executions = Execution.objects.filter(Q(task__exec_status=Task.Done) | Q(task__exec_status=Task.Sent),
                                          task__actual_finish__month=month,
                                          task__actual_finish__year=year)
    inttasks = IntTask.objects.filter(exec_status=IntTask.Done,
                                      actual_finish__month=month,
                                      actual_finish__year=year)

    emails = []

    for employee in employees:

        if employee.user.email:
            otasks = tasks.filter(owner=employee)
            eexecutions = executions.filter(executor=employee)
            einttasks = inttasks.filter(executor=employee)

            if otasks.exists() or eexecutions.exists() or einttasks.exists():
                bonuses = 0
                message = '<html><body>\
                          Шановний(а) {}.<br><br>\
                          За {}.{} Вам були нараховані бонуси за виконання проектів та завдань.<br>\
                          Звірьте їх будь ласка та при необхідності уточніть інформацію у\
                          свого керівника або відповідальної особи по проекту.<br><br>' \
                    .format(employee.user.first_name, month, year)

                if otasks.exists():
                    index = 0
                    message += 'Бонуси за ведення проекту:<br>\
                               <table border="1">\
                               <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                               <th>Тип проекту</th><th>Відсоток</th><th>Бонус</th>'
                    for task in otasks:
                        index += 1
                        message += '<tr>\
                                   <td>{}</td>\
                                   <td><a href="https://erp.itel.rv.ua/project/{}/change/">{}</a></td>\
                                   <td>{:.80}</td>\
                                   <td>{}</td>\
                                   <td>{!s}</td>\
                                   <td>{!s}</td>\
                                   </tr>'. \
                            format(index, task.pk, task.object_code, task.object_address,
                                   task.project_type, task.owner_part(),
                                   round(task.owner_bonus(), 2))
                        bonuses += task.owner_bonus()

                    message += '</table><br>'

                if eexecutions.exists():
                    index = 0
                    message += 'Бонуси за виконання проекту:<br>\
                               <table border="1">\
                               <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                               <th>Тип проекту</th><th>Назва робіт</th><th>Відсоток</th><th>Бонус</th>'

                    for ex in eexecutions:
                        index += 1
                        message += '<tr>\
                                   <td>{}</td>\
                                   <td><a href="http://erp.itel.rv.ua/admin/planner/task/{}/change/">{}</a></td>\
                                   <td>{:.80}</td>\
                                   <td>{}</td>\
                                   <td>{}</td>\
                                   <td>{}</td>\
                                   <td>{!s}</td>\
                                   </tr>'. \
                            format(index, ex.task.pk, ex.task.object_code, ex.task.object_address,
                                   ex.task.project_type, ex.part_name, ex.part,
                                   round(ex.task.exec_bonus(ex.part), 2))
                        bonuses += ex.task.exec_bonus(ex.part)

                    message += '</table><br>'

                if einttasks.exists():
                    index = 0
                    message += 'Бонуси за виконання завдань:<br>\
                               <table border="1">\
                               <th>&#8470;</th><th>Завдання</th><th>Бонус</th>'

                    for task in einttasks:
                        index += 1
                        message += '<tr>\
                                   <td>{}</td>\
                                   <td><a href="http://erp.itel.rv.ua/admin/planner/inttask/{}/change/">{}</a></td>\
                                   <td>{}</td>\
                                   </tr>'. \
                            format(index, task.pk, task.task_name, task.bonus)
                        bonuses += task.bonus

                    message += '</table><br>'

                message += 'Всьго Ви отримаєте {} бонусів.</body></html><br>'.format(
                    round(bonuses, 2))

                emails.append(mail.EmailMessage(
                    'Бонуси за виконання проектів {}.{}'.format(month, year),
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [employee.user.email],
                    ['s.kozlyuk@itel.rv.ua'],
                ))

    for email in emails:
        email.content_subtype = "html"

    connection = mail.get_connection()
    connection.open()
    if connection.send_messages(emails) > 0:
        logger.info("Sent monthly report to employee")
    connection.close()
