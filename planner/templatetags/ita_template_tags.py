import re
from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.conf.locale.uk import formats as uk_formats
from planner.settings import MEDIA_URL, EXECUTION_BADGE_COLORS, TASK_BADGE_COLORS

from planner.models import Execution

register = template.Library()
date_format = uk_formats.DATE_INPUT_FORMATS[0]
time_format = uk_formats.DATETIME_INPUT_FORMATS[0]


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.simple_tag
def url_replace(request, field, value):
    get_values = request.GET.copy()
    get_values[field] = value
    return get_values.urlencode()


@register.simple_tag
def media_url(file_path):
    return MEDIA_URL + str(file_path)


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
def task_overdue_color(status):
    if status.startswith('В черзі'):
        return TASK_BADGE_COLORS['ToDo']
    elif status.startswith('Виконується'):
        return TASK_BADGE_COLORS['InProgress']
    elif status.startswith('Виконано'):
        return TASK_BADGE_COLORS['Done']
    elif status.startswith('Надіслано'):
        return TASK_BADGE_COLORS['Sent']
    elif status.startswith('Призупинено'):
        return TASK_BADGE_COLORS['OnHold']
    elif status.startswith('Відмінено'):
        return TASK_BADGE_COLORS['Canceled']
    elif status.startswith('Очікує'):
        return TASK_BADGE_COLORS['ToDo']
    elif status.startswith('Не'):
        return TASK_BADGE_COLORS['ToDo']
    elif status.startswith('Завершується'):
        return TASK_BADGE_COLORS['ToDo']
    elif status.startswith('Протерміновано'):
        return TASK_BADGE_COLORS['Urgent']
    elif status.startswith('Друк'):
        return TASK_BADGE_COLORS['Print']
    elif status.startswith('Терміново'):
        return TASK_BADGE_COLORS['Urgent']
    elif status.startswith('Коригування'):
        return TASK_BADGE_COLORS['Correction']
    elif re.match(r'^\w', status):
        return TASK_BADGE_COLORS['ManualWarning']
    return


@register.simple_tag
def deal_status_color(status):
    if status.startswith('Оплата'):
        return 'success'
    elif status.startswith('Очікує') or status.startswith('Вартість') or status.startswith('Відсутні'):
        return 'warning'
    elif status.startswith('Закінчується'):
        return 'info'
    elif status.startswith('Протерміновано'):
        return 'danger'
    if re.match(r'^\w', status):
        return 'secondary'
    return


@register.simple_tag
def exec_bonus(task, part):
    return round(task.exec_bonus(part), 2)


@register.simple_tag()
def month_url(request_url, direction='next_month'):
    '''
    next_month return +1 month.
    prev_month return -1 month.
    '''
    request_url = request_url.split('/')
    month = int(request_url[6])
    year = int(request_url[5])
    if direction == 'next_month':
        month += 1
        if month > 12:
            month = 1
            year += 1
    elif direction == 'prev_month':
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    request_url[6] = str(month)
    request_url[5] = str(year)
    url_str = '/'.join(request_url)
    return url_str


@register.simple_tag()
def boolean_to_icon(incoming_value, true_icon, false_icon):
    '''
    required font awesome icons
    sample boolean_to_icon( value, 'far fa-check-circle', 'far fa-times-circle' )
    return: true value with green icon, false value with red icon
    '''
    if incoming_value:
        icon = '<i class="' + true_icon + ' active-success"></i>'
        return format_html(icon)
    else:
        icon = '<i class="' + false_icon + ' active-danger"></i>'
        return format_html(icon)


@register.simple_tag()
def none_date_check(date):
    ''' Return date in rigth format if it exist '''
    if date:
        return date.strftime(date_format)
    return 'Не вказано'


@register.simple_tag()
def none_datetime_check(date):
    ''' Return date in rigth format if it exist '''
    if date:
        return date.strftime(time_format)
    return 'Не вказано'


@register.simple_tag()
def status_change(user, pk, status):
    if status == Execution.ToDo:
        redo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.InProgress})

        redo_styles = 'color: white!important; background-color:' + EXECUTION_BADGE_COLORS['InProgress'] + '!important'
        redo_btn = '<a href="' + redo_url + '"  style="' + redo_styles + '" class="btn btn-sm mx-0">Виконується</a>'
        return format_html(redo_btn)

    elif status == Execution.InProgress:
        undo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.ToDo})
        redo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.OnChecking})

        undo_styles = 'color: black!important; background-color:' + EXECUTION_BADGE_COLORS['ToDo'] + '!important'
        redo_styles = 'color: white!important; background-color:' + EXECUTION_BADGE_COLORS['OnChecking'] + '!important'
        undo_btn = '<a href="' + undo_url + '" style="' + undo_styles + '" class="btn btn-sm mx-0">В черзі</a>'
        redo_btn = '<a href="' + redo_url + '" style="' + redo_styles + '" class="btn btn-sm mx-0">На перевірку</a>'
        if user.groups.filter(name="ГІПи").exists():
            return format_html('<div class="btn-group" role="group">' + undo_btn + redo_btn + '</div>')
        if user.groups.filter(name="Проектувальники").exists():
            return format_html(redo_btn)

    elif status == Execution.OnChecking:
        undo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.InProgress})
        redo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.Done})

        undo_styles = 'color: black!important; background-color:' + EXECUTION_BADGE_COLORS['ToDo'] + '!important'
        redo_styles = 'color: white!important; background-color:' + EXECUTION_BADGE_COLORS['OnChecking'] + '!important'
        undo_btn = '<a href="' + undo_url + '" style="' + undo_styles + '" class="btn btn-sm mx-0">Виконується</a>'
        redo_btn = '<a href="' + redo_url + '" style="' + redo_styles + '" class="btn btn-sm mx-0">Виконано</a>'
        if user.groups.filter(name="ГІПи").exists():
            return format_html('<div class="btn-group" role="group">' + undo_btn + redo_btn + '</div>')
        if user.groups.filter(name="Проектувальники").exists():
            return 'Підзадача на перевірці'

    else:   #status == Execution.Done:
        undo_url = reverse('execution_status_change', kwargs={'pk': pk, 'status': Execution.OnChecking})

        undo_styles = 'color: white!important; background-color:' + EXECUTION_BADGE_COLORS['OnChecking'] + '!important'
        undo_btn = '<a href="' + undo_url + '" style="' + undo_styles + '" class="btn btn-sm mx-0">На перевірку</a>'
        if user.groups.filter(name="ГІПи").exists():
            return format_html('<div class="btn-group" role="group">' + undo_btn + '</div>')
        if user.groups.filter(name="Проектувальники").exists():
            return 'Підзадача закрита'
