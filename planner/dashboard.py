from datetime import date
from django.db.models import Sum

from planner.models import Task, Execution, Deal, Employee, IntTask, News, Event
from analytics.models import Kpi
from eventlog.models import Log


TODAY = date.today()


def context_general(user):

    inttasks = IntTask.objects.filter(executor__user=user)\
                              .exclude(exec_status=IntTask.Done)\
                              .order_by('exec_status')
    hd_inttasks_count = IntTask.objects.filter(executor__user=user,
                                               exec_status=IntTask.Done,
                                               actual_finish__month=TODAY.month,
                                               actual_finish__year=TODAY.year).count()
    active_inttasks_count = IntTask.objects.filter(executor__user=user)\
                                           .exclude(exec_status=IntTask.Done).count()\
                            + hd_inttasks_count
    overdue_inttasks_count = IntTask.objects.filter(executor__user=user)\
                                            .exclude(exec_status=IntTask.Done)\
                                            .exclude(planned_finish__gte=TODAY).count()
    overdue_inttasks_div = int(
        overdue_inttasks_count / active_inttasks_count * 100) if active_inttasks_count > 0 else 0

    bonus = Kpi.objects.filter(employee__user=user,
                               name__in=[Kpi.BonusItel, Kpi.BonusGKP],
                               period__month=TODAY.month,
                               period__year=TODAY.year)\
                       .aggregate(Sum('value'))['value__sum'] or 0
    try:
        inttask_bonus = Kpi.objects.get(employee__user=user,
                                        name=Kpi.Tasks,
                                        period__month=TODAY.month,
                                        period__year=TODAY.year)\
                                   .value
    except Kpi.DoesNotExist:
        inttask_bonus = 0
    total_bonus = bonus + inttask_bonus
    try:
        productivity = Kpi.objects.get(employee__user=user,
                                       name=Kpi.Productivity,
                                       period__month=TODAY.month,
                                       period__year=TODAY.year)\
                                   .value
    except Kpi.DoesNotExist:
        productivity = 0

    news = News.objects.exclude(actual_from__gt=TODAY).exclude(
        actual_to__lte=TODAY).order_by('-created')
    events = Event.objects.filter(
        next_date__isnull=False).order_by('next_date')
    activities = Log.objects.filter(user=user)[:50]

    context = {
        'employee_id': Employee.objects.get(user=user).pk,
        'inttasks': inttasks,
        'active_inttasks_count': active_inttasks_count,
        'overdue_inttasks_count': overdue_inttasks_count,
        'overdue_inttasks_div': overdue_inttasks_div,
        'bonus': bonus,
        'inttask_bonus': inttask_bonus,
        'total_bonus': total_bonus,
        'productivity': int(productivity),
        'news': news,
        'events': events,
        'activities': activities
        }

    return context

def context_accounter(user):

    active_deals = Deal.objects.exclude(act_status=Deal.Issued) \
                               .exclude(number__icontains='загальний')
    actneed_deals = active_deals.filter(exec_status=Deal.Sent)
    unpaid_deals = Deal.objects.exclude(act_status=Deal.NotIssued) \
                               .exclude(pay_status=Deal.PaidUp) \
                               .exclude(number__icontains='загальний')
    debtor_deals = unpaid_deals.filter(exec_status=Deal.Sent)\
                               .exclude(pay_date__isnull=True) \
                               .exclude(pay_date__gte=TODAY)
    overdue_deals = Deal.objects.exclude(exec_status=Deal.Sent) \
                                .exclude(expire_date__gte=TODAY) \
                                .exclude(number__icontains='загальний')

    active_deals_count = active_deals.count()
    actneed_deals_count = actneed_deals.count()
    debtor_deals_count = debtor_deals.count()
    unpaid_deals_count = unpaid_deals.count()
    deals_div = int(actneed_deals_count / active_deals_count *
                    100) if active_deals_count > 0 else 0
    debtor_deals_div = int(
        debtor_deals_count / unpaid_deals_count * 100) if unpaid_deals_count > 0 else 0
    overdue_deals_count = len(overdue_deals)
    overdue_deals_div = int(
        overdue_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0

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

    td_tasks = Task.objects.filter(exec_status=Task.ToDo,
                                   owner__user=user) \
                           .order_by('creation_date')
    ip_tasks = Task.objects.filter(exec_status=Task.InProgress,
                                   owner__user=user) \
                           .order_by('creation_date')
    hd_tasks = Task.objects.filter(exec_status=Task.Done,
                                   owner__user=user) \
                           .order_by('creation_date')
    sent_tasks = Task.objects.filter(owner__user=user,
                                     exec_status=Task.Sent,
                                     actual_finish__month=TODAY.month,
                                     actual_finish__year=TODAY.year)\
                             .order_by('-actual_finish')
    td_tasks_count = td_tasks.count()
    ip_tasks_count = ip_tasks.count()
    hd_tasks_count = hd_tasks.count()
    sent_tasks_count = sent_tasks.count()
    active_tasks_count = Task.objects.filter(owner__user=user).exclude(
        exec_status=Task.Sent).count() + sent_tasks_count
    tasks_div = int(sent_tasks_count / active_tasks_count *
                    100) if active_tasks_count > 0 else 0
    overdue_tasks_count = Task.objects.filter(owner__user=user)\
                                        .exclude(exec_status=Task.Sent)\
                                        .exclude(deal__expire_date__gte=TODAY,
                                                 planned_finish__isnull=True)\
                                        .exclude(deal__expire_date__gte=TODAY,
                                                 planned_finish__gte=TODAY)\
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

    td_executions = Execution.objects.filter(executor__user=user,
                                             exec_status=Execution.ToDo)\
                                        .order_by('creation_date')
    ip_executions = Execution.objects.filter(executor__user=user,
                                             exec_status=Execution.InProgress)\
                                        .order_by('creation_date')
    oc_executions = Execution.objects.filter(executor__user=user,
                                             exec_status=Execution.OnChecking)\
                                        .order_by('creation_date')
    hd_executions = Execution.objects.filter(executor__user=user,
                                             exec_status=Execution.Done,
                                             finish_date__month=TODAY.month,
                                             finish_date__year=TODAY.year)
    td_executions_count = td_executions.count()
    ip_executions_count = ip_executions.count()
    oc_executions_count = oc_executions.count()
    hd_executions_count = hd_executions.count()
    active_executions_count = Execution.objects.filter(executor__user=user)\
                                                .exclude(exec_status=Execution.Done)\
                                                .count() + hd_executions_count
    executions_div = int(hd_executions_count / active_executions_count *
                         100) if active_executions_count > 0 else 0
    overdue_executions_count = Execution.objects.filter(executor__user=user)\
                                        .exclude(exec_status=Execution.Done)\
                                        .exclude(task__deal__expire_date__gte=TODAY,
                                                 task__planned_finish__isnull=True)\
                                        .exclude(task__deal__expire_date__gte=TODAY,
                                                 task__planned_finish__gte=TODAY)\
                                        .count()
    overdue_executions_div = int(
        overdue_executions_count / active_executions_count * 100) if active_executions_count > 0 else 0

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
