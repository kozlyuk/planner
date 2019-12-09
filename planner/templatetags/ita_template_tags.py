import re
from django import template
from django.utils.html import format_html
from planner.settings import MEDIA_URL

register = template.Library()


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
    if status.startswith('Виконано'):
        return 'success'
    elif status.startswith('Очікує') or status.startswith('Не'):
        return 'warning'
    elif status.startswith('Завершити'):
        return 'info'
    elif status.startswith('Протерміновано'):
        return 'danger'
    if re.match(r'^\w', status):
        return 'secondary'
    return


@register.simple_tag
def task_status_color(status):
    if status.startswith('Виконано'):
        return 'success'
    elif status.startswith('В черзі') or status.startswith('Не'):
        return 'warning'
    elif status.startswith('Виконується'):
        return 'info'
    elif status.startswith('Надіслано'):
        return 'primary'
    if re.match(r'^\w', status):
        return 'secondary'
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
def task_secondary_overdue_color(status):
    if status.startswith('Виконується'):
        return 'success'
    elif status.startswith('В очікуванні') or status.startswith('Не'):
        return 'warning'
    elif status.startswith('Виконано'):
        return 'info'
    elif status.startswith('Протерміновано'):
        return 'danger'
    if re.match(r'^\w', status):
        return 'secondary'
    return


@register.simple_tag
def exec_bonus(task, part):
    return round(task.exec_bonus(part), 2)


@register.simple_tag
def calc_summary(summary_value, option='without_currency'):
    '''
    with_currency return * грн. ** коп.
    without_currency return *.**.
    where * is the value
    '''
    if option == 'with_currency':
        if summary_value is None or summary_value is 0:
            return '0 грн. 0 коп.'
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ' грн. ' + summary_value[1] + ' коп.'
    if option == 'without_currency':
        if summary_value is None or summary_value is 0:
            return '0.00'
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ',' + summary_value[1]
    if option == 'vat_with_currency':
        if summary_value is None or summary_value is 0:
            return '0.00'
        summary_value = round(summary_value / 5, 2)
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ' грн. ' + summary_value[1] + ' коп.'


@register.simple_tag
def calc_vat(value, option='without_currency'):
    '''
    with_currency return * грн. ** коп.
    without_currency return *.**.
    where * is the value
    '''
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if option == 'with_currency':
        if value is None or value is 0:
            return '0 грн. 00 коп.'
        vat = round(value + value / 5, 2)
        vat = str(vat).split('.')
        return vat[0] + ' грн. ' + vat[1] + ' коп.'
    if option == 'without_currency':
        if value is None or value is 0:
            return '0.00'
        vat = round(value + value / 5, 2)
        vat = str(vat).split('.')
        return vat[0] + ',' + vat[1]
    return value


@register.simple_tag()
def month_url(request_url, direction='next_month'):
    '''
    next_month return +1 month.
    prev_month return -1 month.
    '''
    request_url = request_url.split('/')
    month = int(request_url[5])
    year = int(request_url[4])
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
    request_url[5] = str(month)
    request_url[4] = str(year)
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
    if date:
        date_string = str(date)
        return date_string.split(maxsplit=1)[0]
    else:
        return 'Дата не вказана'
