from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Q
from django.utils.html import format_html
from django.conf import settings

from planner.models import Task, Execution, Deal, Employee, IntTask
from notice.models import News, Event
from analytics.models import Kpi
from eventlog.models import Log


def executors_rating():
    """ Get list of executors ratings in descending ordering """
    period = date.today().replace(day=1)
    return Kpi.objects.filter(name=Kpi.Productivity, period=period).order_by('-value')


def context_general(user):

    user_inttasks = IntTask.objects.filter(executor__user=user)
    active_inttasks = user_inttasks.exclude(exec_status=IntTask.Done)
    hd_inttasks_count = user_inttasks.filter(exec_status=IntTask.Done,
                                             actual_finish__month=date.today().month,
                                             actual_finish__year=date.today().year).count()
    active_inttasks_count = active_inttasks.count()
    overdue_inttasks_count = active_inttasks.exclude(planned_finish__gte=date.today()).count()
    overdue_inttasks_div = int(overdue_inttasks_count / (active_inttasks_count + hd_inttasks_count) * 100) \
        if active_inttasks_count > 0 else 0

    bonus = Kpi.objects.filter(employee__user=user,
                               name__in=[Kpi.BonusItel, Kpi.BonusGKP, Kpi.BonusSIA],
                               period__month=date.today().month,
                               period__year=date.today().year)\
                       .aggregate(Sum('value'))['value__sum'] or 0
    try:
        inttask_bonus = Kpi.objects.get(employee__user=user,
                                        name=Kpi.Tasks,
                                        period__month=date.today().month,
                                        period__year=date.today().year)\
                                   .value
    except Kpi.DoesNotExist:
        inttask_bonus = 0
    total_bonus = bonus + inttask_bonus
    try:
        productivity = Kpi.objects.get(employee__user=user,
                                       name=Kpi.Productivity,
                                       period__month=date.today().month,
                                       period__year=date.today().year)\
                                   .value
    except Kpi.DoesNotExist:
        productivity = 0

    news = News.objects.exclude(actual_from__gt=date.today()).exclude(
        actual_to__lte=date.today()).order_by('-created')
    events = Event.objects.filter(
        next_date__isnull=False).order_by('next_date')
    if user.is_superuser:
        activities = Log.objects.all()[:200]
    else:
        activities = Log.objects.filter(Q(user=user) | Q(user__employee__head=user.employee))[:100]

    context = {
        'employee_id': Employee.objects.get(user=user).pk,
        'inttasks': active_inttasks,
        'active_inttasks_count': active_inttasks_count,
        'overdue_inttasks_count': overdue_inttasks_count,
        'overdue_inttasks_div': overdue_inttasks_div,
        'bonus': bonus,
        'inttask_bonus': inttask_bonus,
        'total_bonus': total_bonus,
        'productivity': int(productivity),
        'news': news,
        'events': events,
        'activities': activities,
        'executors_rating': executors_rating(),
        }

    return context


def context_accounter(user):

    # Deals tab section
    deals = Deal.objects.all()
    active_deals = deals.exclude(act_status=Deal.Issued) \
                        .exclude(number__icontains='загальний')
    actneed_deals = active_deals.filter(exec_status=Deal.Sent)
    unpaid_deals = deals.exclude(act_status=Deal.NotIssued) \
                        .exclude(pay_status=Deal.PaidUp) \
                        .exclude(number__icontains='загальний')
    debtor_deals = unpaid_deals.filter(exec_status=Deal.Sent)\
                               .exclude(pay_date__isnull=True) \
                               .exclude(pay_date__gte=date.today())
    overdue_deals = deals.exclude(exec_status=Deal.Sent) \
                         .exclude(expire_date__gte=date.today()) \
                         .exclude(number__icontains='загальний')

    active_deals_count = active_deals.count()
    actneed_deals_count = actneed_deals.count()
    debtor_deals_count = debtor_deals.count()
    unpaid_deals_count = unpaid_deals.count()

    # Progress bar section
    deals_div = int(actneed_deals_count / active_deals_count * 100) \
        if active_deals_count > 0 else 0
    debtor_deals_div = int(debtor_deals_count / unpaid_deals_count * 100) \
        if unpaid_deals_count > 0 else 0
    overdue_deals_count = len(overdue_deals)
    overdue_deals_div = int(overdue_deals_count / active_deals_count * 100) \
        if active_deals_count > 0 else 0

    context = {
        'employee': user.employee,
        'actneed_deals': actneed_deals,
        'debtor_deals': debtor_deals,
        'overdue_deals': overdue_deals,
        'actneed_deals_count': actneed_deals_count,
        'active_deals_count': active_deals_count,
        'deals_div': deals_div,
        'debtor_deals_count': debtor_deals_count,
        'unpaid_deals_count': unpaid_deals_count,
        'debtor_deals_div': debtor_deals_div,
        'overdue_deals_count': overdue_deals_count,
        'overdue_deals_div': overdue_deals_div,
        }

    return {**context, **context_general(user)}


def context_pm(user):

    # Projects tab section
    owner_tasks = Task.objects.filter(owner__user=user).order_by('creation_date')
    td_tasks = owner_tasks.filter(exec_status=Task.ToDo)
    td_tasks_count = td_tasks.count()
    ip_tasks = owner_tasks.filter(exec_status=Task.InProgress)
    ip_tasks_count = ip_tasks.count()
    hd_tasks = owner_tasks.filter(exec_status=Task.Done)
    hd_tasks_count = hd_tasks.count()
    sent_tasks = owner_tasks.filter(exec_status=Task.Sent,
                                    actual_finish__month=date.today().month,
                                    actual_finish__year=date.today().year)
    sent_tasks_count = sent_tasks.count()

    # Progress bar section
    active_tasks = owner_tasks.exclude(exec_status__in=[Task.Sent, Task.OnHold, Task.Canceled])
    active_tasks_count = active_tasks.count()
    tasks_div = int(sent_tasks_count / active_tasks_count * 100) \
        if active_tasks_count > 0 else 0
    overdue_tasks_count = active_tasks.exclude(deal__expire_date__gte=date.today(),
                                               planned_finish__isnull=True)\
                                      .exclude(deal__expire_date__gte=date.today(),
                                               planned_finish__gte=date.today())\
                                      .count()
    overdue_tasks_div = int(
        overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0

    context = {
        'employee': user.employee,
        'td_tasks': td_tasks,
        'ip_tasks': ip_tasks,
        'hd_tasks': hd_tasks,
        'sent_tasks': sent_tasks,
        'td_tasks_count': td_tasks_count,
        'ip_tasks_count': ip_tasks_count,
        'hd_tasks_count': hd_tasks_count,
        'sent_tasks_count': sent_tasks_count,
        'active_tasks_count': active_tasks_count,
        'tasks_div': tasks_div,
        'overdue_tasks_count': overdue_tasks_count,
        'overdue_tasks_div': overdue_tasks_div,
        }

    return {**context, **context_general(user)}


def context_projector(user):

    # Tasks tab section
    user_executions = Execution.objects.filter(executor__user=user)
    td_executions = user_executions.filter(exec_status=Execution.ToDo)
    ip_executions = user_executions.filter(exec_status=Execution.InProgress)
    oc_executions = user_executions.filter(exec_status=Execution.OnChecking)
    hd_executions = user_executions.filter(exec_status=Execution.Done,
                                           finish_date__month=date.today().month,
                                           finish_date__year=date.today().year)
    td_executions_count = td_executions.count()
    ip_executions_count = ip_executions.count()
    oc_executions_count = oc_executions.count()
    hd_executions_count = hd_executions.count()

    # Progress bar section
    active_executions_count = user_executions.exclude(exec_status=Execution.Done)\
                                             .count() + hd_executions_count
    executions_div = int(hd_executions_count / active_executions_count *
                         100) if active_executions_count > 0 else 0
    overdue_executions_count = user_executions.exclude(exec_status=Execution.Done)\
                                              .exclude(task__deal__expire_date__gte=date.today(),
                                                       task__planned_finish__isnull=True)\
                                              .exclude(task__deal__expire_date__gte=date.today(),
                                                       task__planned_finish__gte=date.today())\
                                              .count()
    overdue_executions_div = int(overdue_executions_count / active_executions_count * 100) \
        if active_executions_count > 0 else 0

    context = {
        'employee': user.employee,
        'td_executions': td_executions,
        'ip_executions': ip_executions,
        'oc_executions': oc_executions,
        'hd_executions': hd_executions,
        'td_executions_count': td_executions_count,
        'ip_executions_count': ip_executions_count,
        'oc_executions_count': oc_executions_count,
        'hd_executions_count': hd_executions_count,
        'active_executions_count': active_executions_count,
        'executions_div': executions_div,
        'overdue_executions_count': overdue_executions_count,
        'overdue_executions_div': overdue_executions_div,
        }

    return {**context, **context_general(user)}


def context_bonus_per_month(employee, period):

    # get owner tasks
    labels_task = ["№",
                   Task._meta.get_field('object_code').verbose_name,
                   Task._meta.get_field('object_address').verbose_name,
                   Task._meta.get_field('project_type').verbose_name,
                   Task.owner_part.short_description,
                   Task.owner_bonus.short_description,
                   Task._meta.get_field('actual_finish').verbose_name,
                   Task._meta.get_field('sending_date').verbose_name,
                   ]
    tasks = employee.tasks_for_period(period)
    bonuses = 0
    index = 0
    task_list = []
    for task in tasks:
        index += 1
        owner_bonus = task.owner_bonus().quantize(Decimal("1.00"), ROUND_HALF_UP)
        task_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         task.get_absolute_url(),
                                         task.object_code)),
                          task.object_address,
                          task.project_type,
                          task.owner_part(),
                          owner_bonus,
                          task.actual_finish,
                          task.sending_date
                          ])
        bonuses += owner_bonus
    # get executions
    labels_execution = ["№",
                        Task._meta.get_field('object_code').verbose_name,
                        Task._meta.get_field('object_address').verbose_name,
                        Task._meta.get_field('project_type').verbose_name,
                        Execution._meta.get_field('part_name').verbose_name,
                        Execution._meta.get_field('part').verbose_name,
                        Task.exec_bonus.short_description,
                        Execution._meta.get_field('finish_date').verbose_name,
                        ]
    executions = employee.executions_for_period(period)
    index = 0
    executions_list = []
    for ex in executions:
        index += 1
        exec_bonus = ex.task.exec_bonus(ex.part).quantize(Decimal("1.00"), ROUND_HALF_UP)
        executions_list.append([index,
                                format_html('<a href="%s%s">%s</a>'
                                            % (settings.SITE_URL,
                                               ex.task.get_absolute_url(),
                                               ex.task.object_code)),
                                ex.task.object_address,
                                ex.task.project_type,
                                ex.part_name,
                                ex.part,
                                exec_bonus,
                                ex.finish_date
                                ])
        bonuses += exec_bonus
    # get inttasks
    labels_inttask = ["№",
                      IntTask._meta.get_field('task_name').verbose_name,
                      IntTask._meta.get_field('bonus').verbose_name,
                      ]
    inttasks = employee.inttasks_for_period(period)
    index = 0
    inttasks_list = []
    for task in inttasks:
        index += 1
        inttasks_list.append([index,
                              format_html('<a href="%s%s">%s</a>'
                                          % (settings.SITE_URL,
                                             task.get_absolute_url(),
                                             task.task_name)),
                              task.bonus
                              ])
        bonuses += task.bonus
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels_task': labels_task,
        'labels_execution': labels_execution,
        'labels_inttask': labels_inttask,
        'tasks': task_list,
        'executions': executions_list,
        'inttasks': inttasks_list,
        'bonuses': bonuses,
        'month': period.month,
        'year': period.year
    }
    return context


def context_deal_calculation(deal):

    # get tasks
    tasks = Task.objects.filter(deal=deal)
    objects = tasks.values('object_code', 'object_address').order_by().distinct()
    project_types = tasks.values('project_type__price_code',
                                 'project_type__project_type',
                                 'project_type__price') \
                         .order_by('project_type__price_code').distinct()
    # prepare table data
    index = 0
    svalue = Decimal(0)
    object_lists = []
    for ptype in project_types:
        if ptype['project_type__price'] != 0:
            index += 1
            object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code']) \
                                .values_list('object_code', flat=True)
            object_list = ''
            for obj in object_codes:
                object_list += obj + ' '
            count = object_codes.count()
            price = ptype['project_type__price'] / Decimal(1.2)
            price = price.quantize(Decimal("1.00"), ROUND_HALF_UP)
            value = price * count
            svalue += value
            object_lists.append([index, f"{ptype['project_type__project_type']} {object_list}",
                                 "об'єкт", count, price, value])
    # creating context
    context = {
        'deal': deal,
        'objects': objects,
        'taxation': deal.company.taxation,
        'object_lists': object_lists,
        'svalue': svalue
    }
    return context
