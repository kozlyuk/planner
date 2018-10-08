# -*- coding: utf-8 -*-
from django import template

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):
    get_values = request.GET.copy()
    get_values[field] = value
    return get_values.urlencode()


@register.filter(name='proper_paginate')
def proper_paginate(paginator, current_page, neighbors=10):
    if paginator.num_pages > 2*neighbors:
        start_index = max(1, current_page-neighbors)
        end_index = min(paginator.num_pages, current_page + neighbors)
        if end_index < start_index + 2*neighbors:
            end_index = start_index + 2*neighbors
        elif start_index > end_index - 2*neighbors:
            start_index = end_index - 2*neighbors
        if start_index < 1:
            end_index -= start_index
            start_index = 1
        elif end_index > paginator.num_pages:
            start_index -= (end_index-paginator.num_pages)
            end_index = paginator.num_pages
        page_list = [f for f in range(start_index, end_index+1)]
        return page_list[:(2*neighbors + 1)]
    return paginator.page_range


@register.simple_tag
def task_status_color(status):
    if status == 'ST':
        return 'success'
    elif status == 'HD':
        return 'warning'
    elif status == 'IW':
        return 'info'
    else:
        return 'danger'


@register.simple_tag
def deal_status_color(status):
    if status.startswith('Оплата'):
        return 'success'
    elif status.startswith('Очікує') or status.startswith('Вартість'):
        return 'warning'
    elif status.startswith('Закінчується'):
        return 'info'
    elif status.startswith('Протерміновано'):
        return 'danger'
    else:
        return


@register.simple_tag
def exec_bonus(task, part):
    return round(task.exec_bonus(part), 2)