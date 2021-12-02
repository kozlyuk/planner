from datetime import date
from django.db.models import Sum, Q

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
    debtor_deals = unpaid_deals.filter(act_status=Deal.Issued,
                                       pay_status__in=[Deal.NotPaid, Deal.AdvancePaid])
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
