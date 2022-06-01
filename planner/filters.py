from datetime import datetime, date, timedelta
from django.db.models import Q

from .models import Employee, Task, Execution


def task_queryset_filter(request_user, query_dict):
    """Filter for the Task class
    Filter queryset by search_string ('filter' get parameter)
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by owners ('owner' get parameters list)
    Filter queryset by customers ('customer' get parameters list)
    Filter queryset by constructions ('construction' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Order queryset by any given field ('o' get parameter)
    """

    search_string = query_dict.get('filter', '').split()
    exec_statuses = list(filter(None, query_dict.getlist('exec_status')))
    owners = list(filter(None, query_dict.getlist('owner')))
    customers = list(filter(None, query_dict.getlist('customer')))
    constructions = list(filter(None, query_dict.getlist('construction')))
    work_types = list(filter(None, query_dict.getlist('work_type')))
    order = query_dict.get('o')


    tasks = Task.objects.all().select_related('project_type', 'owner', 'deal', 'deal__customer')
    # filter only customer tasks
    if request_user.groups.filter(name='Замовники').exists():
        tasks = tasks.filter(deal__customer__user=request_user)
    for word in search_string:
        tasks = tasks.filter(Q(object_code__icontains=word) |
                                Q(object_address__icontains=word) |
                                Q(deal__number__icontains=word) |
                                Q(project_type__price_code__icontains=word) |
                                Q(project_type__project_type__icontains=word))
    if exec_statuses:
        tasks_union = Task.objects.none()
        for status in exec_statuses:
            tasks_segment = tasks.filter(exec_status=status)
            tasks_union = tasks_union | tasks_segment
        tasks = tasks_union
    if owners:
        tasks_union = Task.objects.none()
        for owner in owners:
            tasks_segment = tasks.filter(owner=owner)
            tasks_union = tasks_union | tasks_segment
        tasks = tasks_union
    if customers:
        tasks_union = Task.objects.none()
        for customer in customers:
            tasks_segment = tasks.filter(deal__customer=customer)
            tasks_union = tasks_union | tasks_segment
        tasks = tasks_union
    if constructions:
        tasks_union = Task.objects.none()
        for construction in constructions:
            tasks_segment = tasks.filter(construction=construction)
            tasks_union = tasks_union | tasks_segment
        tasks = tasks_union
    if work_types:
        tasks_union = Task.objects.none()
        for work_type in work_types:
            tasks_part = tasks.filter(work_type=work_type)
            tasks_union = tasks_union | tasks_part
        tasks = tasks_union
    if order:
        tasks = tasks.order_by(order)
    else:
        tasks = tasks.order_by('-creation_date', '-deal', 'object_code')
    return tasks


def execuition_queryset_filter(request_user, query_dict):
    """Filter for the Execution class
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Filter queryset by owner ('owner' get parameter)
    Filter queryset by executor ('executor' get parameter)
    Filter queryset by company ('company' get parameter)
    Filter queryset by planned_start ('planned_start' get parameter)
    Filter queryset by planned_finish ('planned_finish' get parameter)
    Filter queryset by search_string ('filter' get parameter)
    Order queryset by any given field ('o' get parameter)
    """

    exec_statuses = list(filter(None, query_dict.getlist('exec_status')))
    work_types = list(filter(None, query_dict.getlist('work_type')))
    owner = query_dict.get('owner')
    executor = query_dict.get('executor')
    company = query_dict.get('company')
    planned_start = query_dict.get('actual_start')
    planned_finish = query_dict.get('actual_finish')
    search_string = query_dict.get('filter', '').split()
    order = query_dict.get('o')

    # create qs tasks
    executions = Execution.objects.filter(subtask__add_to_schedule=True) \
                             .select_related('executor', 'task', 'task__deal')
    if request_user.is_superuser:
        pass
    else:
        query = Q()
        if request_user.groups.filter(name='Замовники').exists():
            query |= Q(task__deal__customer__user=request_user,
                       subtask__show_to_customer=True)
        if request_user.groups.filter(name='ГІПи').exists():
            query |= Q(executor__head=request_user.employee)
        if request_user.groups.filter(name='Проектувальники').exists():
            query |= Q(executor=request_user.employee)
        executions = executions.filter(query)

    if exec_statuses:
        tasks_union = Execution.objects.none()
        for status in exec_statuses:
            tasks_part = executions.filter(exec_status=status)
            tasks_union = tasks_union | tasks_part
        executions = tasks_union
    if work_types:
        tasks_union = Execution.objects.none()
        for work_type in work_types:
            tasks_part = executions.filter(task__work_type=work_type)
            tasks_union = tasks_union | tasks_part
        executions = tasks_union
    if owner:
        executions = executions.filter(task__owner=owner)
    if executor:
        executions = executions.filter(executor=executor)
    if company:
        executions = executions.filter(task__deal__company=company)
    if planned_start:
        planned_start_value = datetime.strptime(planned_start, '%Y-%m-%d')
    else:
        planned_start_value = date.today() - timedelta(days=date.today().weekday())
    if planned_finish:
        planned_finish_value = datetime.strptime(planned_finish, '%Y-%m-%d')
    else:
        planned_finish_value = planned_start_value + timedelta(days=14)
    executions = executions.filter(Q(planned_start__gte=planned_start_value, planned_start__lte=planned_finish_value) |
                         Q(planned_finish__gte=planned_start_value, planned_finish__lte=planned_finish_value) |
                         Q(planned_start__lt=planned_start_value,
                           exec_status=[Execution.ToDo, Execution.InProgress, Execution.OnChecking, Execution.OnHold]) |
                         Q(planned_finish__lt=planned_start_value,
                           exec_status__in=[Execution.ToDo, Execution.InProgress, Execution.OnChecking, Execution.OnHold])
                         ) \
                 .exclude(task__exec_status__in=[Task.OnHold, Task.Canceled])
    for word in search_string:
        executions = executions.filter(Q(subtask__name__icontains=word) |
                             Q(task__object_code__icontains=word) |
                             Q(task__project_type__project_type__icontains=word) |
                             Q(task__object_address__icontains=word) |
                             Q(task__deal__number__icontains=word))
    if order:
        executions = executions.order_by(order, 'planned_start')
    else:
        executions = executions.order_by('planned_start')
    return executions.distinct(), planned_start_value, planned_finish_value


def employee_queryset_filter(request_user, query_dict):
    """
    Filter for the Execution class grouped by emplyees
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Filter queryset by owner ('owner' get parameter)
    Filter queryset by company ('company' get parameter)
    Filter queryset by planned_start ('planned_start' get parameter)
    Filter queryset by planned_finish ('planned_finish' get parameter)
    Filter queryset by search_string ('filter' get parameter)
    Order queryset by any given field ('o' get parameter)
    """

    # create qs employees
    employees = Employee.objects.filter(user__is_active=True)

    return employees
