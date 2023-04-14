from decimal import Decimal, ROUND_HALF_UP
from django.utils.html import format_html
from django.conf import settings

from planner.models import Task, Execution, IntTask, Deal

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
        owner_bonus = task.owner_bonus()
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
                        Execution._meta.get_field('subtask').verbose_name,
                        Execution._meta.get_field('part').verbose_name,
                        Task.exec_bonus.short_description,
                        Execution._meta.get_field('actual_finish').verbose_name,
                        ]
    executions = employee.executions_for_period(period)
    index = 0
    executions_list = []
    for ex in executions:
        index += 1
        exec_bonus = ex.task.exec_bonus(ex.part)
        executions_list.append([index,
                                format_html('<a href="%s%s">%s</a>'
                                            % (settings.SITE_URL,
                                               ex.task.get_absolute_url(),
                                               ex.task.object_code)),
                                ex.task.object_address,
                                ex.task.project_type,
                                ex.subtask.name,
                                ex.part,
                                exec_bonus,
                                ex.actual_finish
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


def context_deal_render(deal):

    # get tasks
    tasks = Task.objects.filter(deal=deal)
    objects = tasks.values('object_code', 'object_address').order_by().distinct()
    project_types = tasks.values('project_type__price_code',
                                 'project_type__project_type',
                                 'project_type__price') \
                         .order_by('project_type__price_code').distinct()

    # prepare table data
    deal_term = deal.expire_date - deal.date
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
            price_code = ptype['project_type__price_code'].split('.', 1)[1]
            object_lists.append([index,
                                 price_code,
                                 ptype['project_type__project_type'],
                                 object_list,
                                 "об'єкт",
                                 count,
                                 price,
                                 value])
    # creating context
    context = {
        'deal': deal,
        'objects': objects,
        'taxation': deal.company.taxation,
        'object_lists': object_lists,
        'svalue': svalue,
        'advance': deal.advance,
        'overpay': deal.value - deal.advance,
        'deal_term': deal_term.days
    }
    return context


def context_act_render(act):

    # get tasks
    tasks = Task.objects.filter(act_of_acceptance=act)
    # prepare object_list data
    index = 0
    svalue = Decimal(0)
    svalue_w_vat = Decimal(0)
    count = 1
    object_list = []
    for task in tasks:
        if task.project_type.price != 0:
            index += 1
            price_wo_vat = task.project_type.price / Decimal(1.2)
            price_wo_vat = price_wo_vat.quantize(Decimal("1.00"), ROUND_HALF_UP)
            svalue += price_wo_vat * count
            svalue_w_vat += task.project_type.price * count
            price_code = task.project_type.price_code.split('.', 1)[1]
            object_list.append([index,
                                task.object_code,
                                task.object_address,
                                f'{price_code}. {task.project_type.description}',
                                count,
                                price_wo_vat,
                                task.project_type.price,
                                ])

    # prepare groped_list data
    grouped_list = []
    index = 0
    project_types = tasks.values('project_type__price_code',
                                 'project_type__project_type',
                                 'project_type__price') \
                         .order_by('project_type__price_code').distinct()
    for ptype in project_types:
        if ptype['project_type__price'] != 0:
            index += 1
            object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code']) \
                                .values_list('object_code', flat=True)
            objects = ''
            for obj in object_codes:
                objects += obj + ', '
            objects = objects[:-2]
            count = object_codes.count()
            price = ptype['project_type__price'] / Decimal(1.2)
            price = price.quantize(Decimal("1.00"), ROUND_HALF_UP)
            value = price * count
            price_code = ptype['project_type__price_code'].split('.', 1)[1]
            grouped_list.append([index,
                                 price_code,
                                 ptype['project_type__project_type'],
                                 objects,
                                 "об'єкт",
                                 count,
                                 price,
                                 value])

    objects = tasks.values('object_code', 'object_address').order_by().distinct()

    # creating context
    context = {
        'act': act,
        'deal': act.deal,
        'objects': objects,
        'object_list': object_list,
        'grouped_list': grouped_list,
        'svalue': svalue,
        'svalue_w_vat': svalue_w_vat,
        'taxation': act.deal.company.taxation,
    }

    return context
