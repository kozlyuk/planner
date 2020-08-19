from datetime import date
from django.utils.html import format_html
from django.conf import settings

from planner.models import Task, Execution, Deal, IntTask


TODAY = date.today()


def context_actneed_deals(deals, employee):

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('customer').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              ]
    index = 0
    deal_list = []
    for deal in deals:
        index += 1
        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.customer,
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display()
                          ])
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels': labels,
        'deals': deal_list
    }
    return context


def context_debtors_deals(deals, employee):

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('customer').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
              ]
    index = 0
    deal_list = []
    for deal in deals:
        index += 1
        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.customer,
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.get_exec_status_display()
                          ])
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels': labels,
        'deals': deal_list
    }
    return context


def context_overdue_deals(deals, employee):

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('customer').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('expire_date').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
              ]
    index = 0
    deal_list = []
    for deal in deals:
        index += 1
        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.customer,
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.expire_date,
                          deal.get_exec_status_display()
                          ])
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels': labels,
        'deals': deal_list
    }
    return context


def context_overdue_tasks(employee):

    # get owner tasks
    labels_task = ["№",
                   Task._meta.get_field('object_code').verbose_name,
                   Task._meta.get_field('object_address').verbose_name,
                   Task._meta.get_field('project_type').verbose_name,
                   Task._meta.get_field('exec_status').verbose_name,
                   Task._meta.get_field('planned_finish').verbose_name,
                   Task._meta.get_field('warning').verbose_name,
                   ]
    tasks = employee.overdue_tasks()
    index = 0
    task_list = []
    for task in tasks:
        index += 1
        task_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         task.get_absolute_url(),
                                         task.object_code)),
                          task.object_address,
                          task.project_type,
                          task.get_exec_status_display(),
                          task.planned_finish,
                          task.warning
                          ])
    # get executions
    labels_execution = ["№",
                        Task._meta.get_field('object_code').verbose_name,
                        Task._meta.get_field('object_address').verbose_name,
                        Task._meta.get_field('project_type').verbose_name,
                        Execution._meta.get_field('part_name').verbose_name,
                        Execution._meta.get_field('planned_finish').verbose_name,
                        Execution._meta.get_field('warning').verbose_name,
                        ]
    executions = employee.overdue_executions()
    index = 0
    executions_list = []
    for ex in executions:
        index += 1
        executions_list.append([index,
                                format_html('<a href="%s%s">%s</a>'
                                            % (settings.SITE_URL,
                                               ex.task.get_absolute_url(),
                                               ex.task.object_code)),
                                ex.task.object_address,
                                ex.task.project_type,
                                ex.part_name,
                                ex.planned_finish,
                                ex.warning
                                ])
    # get inttasks
    labels_inttask = ["№",
                      IntTask._meta.get_field('task_name').verbose_name,
                      IntTask._meta.get_field('planned_finish').verbose_name,
                      ]
    inttasks = employee.overdue_inttasks()
    index = 0
    inttasks_list = []
    for task in inttasks:
        index += 1
        inttasks_list.append([index,
                              format_html('<a href="%s%s">%s</a>'
                                          % (settings.SITE_URL,
                                             task.get_absolute_url(),
                                             task.task_name)),
                              task.planned_finish
                              ])
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels_task': labels_task,
        'labels_execution': labels_execution,
        'labels_inttask': labels_inttask,
        'tasks': task_list,
        'executions': executions_list,
        'inttasks': inttasks_list,
    }
    return context


def context_unsent_tasks(employee):

    # get owner tasks
    labels_task = ["№",
                   Task._meta.get_field('object_code').verbose_name,
                   Task._meta.get_field('object_address').verbose_name,
                   Task._meta.get_field('project_type').verbose_name,
                   Task._meta.get_field('exec_status').verbose_name,
                   Task._meta.get_field('actual_finish').verbose_name,
                   Task._meta.get_field('warning').verbose_name,
                   ]
    tasks = employee.unsent_tasks()
    index = 0
    task_list = []
    for task in tasks:
        index += 1
        task_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         task.get_absolute_url(),
                                         task.object_code)),
                          task.object_address,
                          task.project_type,
                          task.get_exec_status_display(),
                          task.actual_finish,
                          task.warning
                          ])
    # creating context
    context = {
        'first_name': employee.user.first_name,
        'labels_task': labels_task,
        'tasks': task_list,
    }
    return context
