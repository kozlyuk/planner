from datetime import date, timedelta
from celery.utils.log import get_task_logger
from django.conf.locale.uk import formats as uk_formats

from planner.models import Deal, Task
from planner.celery import app

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
        elif Task.Sent in tasks:
            exec_status = Deal.Sent
        elif Task.Canceled in tasks:
            exec_status = Deal.Canceled
        else:
            exec_status = Deal.ToDo

        if deal.manual_warning:
            warning = deal.manual_warning
        elif deal.task_set.all().count() == 0:
            warning = 'Відсутні проекти'
        elif exec_status == Deal.Canceled:
                warning = 'Відмінено'
        elif exec_status == Deal.Sent:
            value_calc = deal.value_calc() + deal.value_correction
            if deal.value > 0 and deal.value != value_calc:
                warning = 'Вартість по роботам %s' % value_calc
            elif deal.act_status in [deal.NotIssued, deal.PartlyIssued]:
                warning = 'Очікує закриття акту'
            elif deal.pay_status != deal.PaidUp and deal.pay_date_calc():
                warning = 'Оплата %s' % deal.pay_date_calc().strftime(date_format)
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
