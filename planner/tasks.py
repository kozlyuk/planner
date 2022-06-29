from datetime import date, timedelta
from celery.utils.log import get_task_logger
from django.db.models import F
from django.conf.locale.uk import formats as uk_formats

from planner.models import Deal, Task, Execution
from planner.celery import app

date_format = uk_formats.DATE_INPUT_FORMATS[0]
logger = get_task_logger(__name__)


@app.task
def update_task_statuses(task_id=None):
    """ Update statuses. If task_id given updates for task_id else updates for last 500 tasks """
    if task_id:
        tasks = Task.objects.filter(pk=task_id)
    else:
        tasks = Task.objects.order_by('-id').prefetch_related('execution_set')[:500]
    task_list = []
    for task in tasks:
        # update warning
        sending_status = task.sending_status()
        if task.manual_warning:
            task.warning = task.manual_warning
        elif task.exec_status == Task.OnHold:
            task.warning = 'Призупинено'
        elif task.exec_status == Task.Canceled:
            task.warning = 'Відмінено'
        elif task.exec_status == Task.Done and sending_status != 'Надіслано':
            task.warning = sending_status
        elif task.exec_status in [Task.Sent, Task.Done] and task.actual_finish:
            task.warning = 'Виконано %s' % task.actual_finish.strftime(date_format)
        elif task.execution_status() == 'Виконано':
            task.warning = 'Очікує на перевірку'
        elif task.planned_finish:
            if task.planned_finish < date.today():
                task.warning = 'Протерміновано %s' % task.planned_finish.strftime(
                    date_format)
            elif task.planned_finish - timedelta(days=7) <= date.today():
                task.warning = 'Завершується %s' % task.planned_finish.strftime(
                    date_format)
            else:
                task.warning = 'Завершити до %s' % task.planned_finish.strftime(
                    date_format)
        elif task.deal.expire_date < date.today():
            task.warning = 'Протерміновано %s' % task.deal.expire_date.strftime(
                date_format)
        elif task.deal.expire_date - timedelta(days=7) <= date.today():
            task.warning = 'Завершується %s' % task.deal.expire_date.strftime(
                date_format)
        else:
            task.warning = 'Завершити до %s' % task.deal.expire_date.strftime(
                date_format)

        # update planned_start and planner_finish
        if task.exec_status in [Task.ToDo, Task.InProgress, Task.Done] and task.execution_set.exists():
            # planned_start = task.execution_set.order_by(F('planned_start').asc(nulls_last=True)).first().planned_start
            # task.planned_start = planned_start.date() if planned_start else None
            if not task.execution_set.filter(planned_finish__isnull=True).exists():
                task.planned_finish = task.execution_set.order_by('planned_finish').last().planned_finish.date()

        task_list.append(task)

    Task.objects.bulk_update(task_list, ['warning', 'planned_start', 'planned_finish'])
    logger.info("Tasks warning and planned dates updated. %s", task_id)


@app.task
def update_deal_statuses(deal_id=None):
    """ Update statuses and warnings. If deal_id given updates for deal_id else updates for last 200 deals """
    if deal_id:
        deals = Deal.objects.filter(pk=deal_id)
    else:
        deals = Deal.objects.order_by('-id').prefetch_related('task_set')[:200]
    deal_list = []
    for deal in deals:
        tasks = deal.task_set.values_list('exec_status', flat=True)
        if Task.ToDo in tasks:
            deal.exec_status = Deal.ToDo
        elif Task.InProgress in tasks:
            deal.exec_status = Deal.InProgress
        elif Task.Done in tasks:
            deal.exec_status = Deal.Done
        elif Task.Sent in tasks:
            deal.exec_status = Deal.Sent
        elif Task.Canceled in tasks:
            deal.exec_status = Deal.Canceled
        else:
            deal.exec_status = Deal.ToDo

        if deal.manual_warning:
            deal.warning = deal.manual_warning
        elif deal.task_set.all().count() == 0:
            deal.warning = 'Відсутні проекти'
        elif deal.exec_status == Deal.Canceled:
                deal.warning = 'Відмінено'
        elif deal.exec_status == Deal.Sent:
            value_calc = deal.value_calc() + deal.value_correction
            if deal.value > 0 and deal.value != value_calc:
                deal.warning = 'Вартість по роботам %s' % value_calc
            elif deal.act_status in [deal.NotIssued, deal.PartlyIssued]:
                deal.warning = 'Очікує закриття акту'
            elif deal.pay_status != deal.PaidUp and deal.pay_date_calc():
                deal.warning = 'Оплата %s' % deal.pay_date_calc().strftime(date_format)
            else:
                deal.warning = ''
        elif deal.expire_date < date.today():
            deal.warning = 'Протерміновано %s' % deal.expire_date.strftime(
                date_format)
        elif deal.expire_date - timedelta(days=7) <= date.today():
            deal.warning = 'Закінчується %s' % deal.expire_date.strftime(
                date_format)
        else:
            deal.warning = ''

        deal_list.append(deal)

    Deal.objects.bulk_update(deal_list, ['exec_status', 'warning'])
    logger.info("Deal statuses and warnings updated. %s", deal_id)
