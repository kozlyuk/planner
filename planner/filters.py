from datetime import datetime, date, timedelta
from django.db.models import Q

from .models import Deal, Employee, Task, Execution, Order


def deal_queryset_filter(request_user, query_dict):
    """
    Filter for the Deal queryset
    Filter queryset by search_string ('filter' get parameter)
    Filter queryset by customers ('customer' get parameters list)
    Filter queryset by companys ('company' get parameters list)
    Filter queryset by act_statuses ('act_status' get parameters list)
    Filter queryset by pay_statuses ('pay_status' get parameters list)
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by specific_status ('specific_status' get parameters list)
    Order queryset by any given field ('o' get parameter)
    """
    search_string = query_dict.get('filter', '').split()
    customers = query_dict.getlist('customer', '0')
    companies = query_dict.getlist('company', '0')
    act_statuses = query_dict.getlist('act_status', '0')
    pay_statuses = query_dict.getlist('pay_status', '0')
    exec_statuses = query_dict.getlist('exec_status', '0')
    specific_status = query_dict.get('specific_status', '0')
    start_date = query_dict.get('start_date', '0')
    end_date = query_dict.get('end_date', '0')
    order = query_dict.get('o', '0')

    deals = Deal.objects.select_related('customer', 'company')
    if specific_status == 'WA':
        deals = deals.waiting_for_act()
    if specific_status == 'PQ':
        deals = deals.payment_queue()
    if specific_status == 'OP':
        deals = deals.overdue_payment()
    if specific_status == 'OE':
        deals = deals.overdue_execution()
    if specific_status == 'RE':
        deals = deals.receivables()

    for word in search_string:
        deals = deals.filter(Q(number__icontains=word) |
                                Q(value__icontains=word))

    if customers != '0':
        deals_union = Deal.objects.none()
        for customer in customers:
            deals_part = deals.filter(customer=customer)
            deals_union = deals_union | deals_part
        deals = deals_union
    if companies != '0':
        deals_union = Deal.objects.none()
        for company in companies:
            deals_part = deals.filter(company=company)
            deals_union = deals_union | deals_part
        deals = deals_union
    if act_statuses != '0':
        deals_union = Deal.objects.none()
        for act_status in act_statuses:
            deals_part = deals.filter(act_status=act_status)
            deals_union = deals_union | deals_part
        deals = deals_union
    if pay_statuses != '0':
        deals_union = Deal.objects.none()
        for pay_status in pay_statuses:
            deals_part = deals.filter(pay_status=pay_status)
            deals_union = deals_union | deals_part
        deals = deals_union
    if exec_statuses != '0':
        deals_union = Deal.objects.none()
        for exec_status in exec_statuses:
            deals_part = deals.filter(exec_status=exec_status)
            deals_union = deals_union | deals_part
        deals = deals_union
    if start_date:
        start_value = datetime.strptime(start_date, '%Y-%m-%d')
        deals = deals.filter(date__gte=start_value)
    if end_date:
        finish_value = datetime.strptime(end_date, '%Y-%m-%d')
        deals = deals.filter(date__lte=finish_value)
    if order != '0':
        deals = deals.order_by(order)
    return deals


def task_queryset_filter(request_user, query_dict):
    """
    Filter for the Task class
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
    period_month = query_dict.get('period_month')
    period_year = query_dict.get('period_year')
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
    if period_month and period_month != '0':
        tasks = tasks.filter(period__month=period_month)
    if period_year and period_year != '0':
        tasks = tasks.filter(period__year=period_year)
    if order:
        tasks = tasks.order_by(order)
    else:
        tasks = tasks.order_by('-creation_date', '-deal', 'object_code')
    return tasks


def execuition_queryset_filter(request_user, query_dict):
    """
    Filter for the Execution class
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
    Filter for the Employee queryset
    """

    # create qs employees
    employees = Employee.objects.filter(user__is_active=True)

    return employees


def order_queryset_filter(request_user, query_dict):
    """
    Filter for the Order queryset
    Filter queryset by search_string ('filter' get parameter)
    Filter queryset by contractors ('contractor' get parameters list)
    Filter queryset by pay_statuses ('pay_status' get parameters list)
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by constructions ('construction' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Order queryset by any given field ('o' get parameter)
    """

    search_string = query_dict.get('filter', '').split()
    contractors = list(filter(None, query_dict.getlist('contractor')))
    companies = list(filter(None, query_dict.getlist('company')))
    pay_statuses = list(filter(None, query_dict.getlist('pay_status')))
    exec_statuses = list(filter(None, query_dict.getlist('exec_status')))
    pay_types = list(filter(None, query_dict.getlist('pay_type')))
    owners = list(filter(None, query_dict.getlist('owner')))
    cost_types = list(filter(None, query_dict.getlist('cost_type')))
    order = query_dict.get('o')

    orders = Order.objects.all().select_related('contractor', 'task', 'subtask')
    # filter only customer tasks
    if not request_user.is_superuser \
        and not request_user.groups.filter(name='Секретарі').exists() \
        and request_user.groups.filter(name='ГІПи').exists():
            orders = orders.filter(task__owner__user=request_user)

    for word in search_string:
        orders = orders.filter(Q(contractor__name__icontains=word) |
                               Q(task__object_code__icontains=word) |
                               Q(subtask__name__icontains=word) |
                               Q(purpose__icontains=word) |
                               Q(deal_number__icontains=word)
                               )
    if contractors:
        orders_union = Order.objects.none()
        for contractor in contractors:
            orders_segment = orders.filter(contractor=contractor)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if companies:
        orders_union = Order.objects.none()
        for company in companies:
            orders_segment = orders.filter(company=company)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if pay_statuses:
        orders_union = Order.objects.none()
        for status in pay_statuses:
            orders_segment = orders.filter(pay_status=status)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if exec_statuses:
        orders_union = Order.objects.none()
        for status in exec_statuses:
            orders_segment = orders.filter(task__exec_status=status)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if pay_types:
        orders_union = Order.objects.none()
        for pay_type in pay_types:
            orders_segment = orders.filter(pay_type=pay_type)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if owners:
        orders_union = Order.objects.none()
        for owner in owners:
            orders_segment = orders.filter(task__owner=owner)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if cost_types:
        orders_union = Order.objects.none()
        for cost_type in cost_types:
            orders_segment = orders.filter(cost_type=cost_type)
            orders_union = orders_union | orders_segment
        orders = orders_union
    if order:
        orders = orders.order_by(order)
    else:
        orders = orders.order_by('-creation_date', 'contractor')
    return orders
