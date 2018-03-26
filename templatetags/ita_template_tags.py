# -*- coding: utf-8 -*-
from django import template
from django.core.files.storage import default_storage
from django.contrib.auth.models import Group

register = template.Library()


@register.filter(name='file_exists')
def file_exists(filepath):
    if default_storage.exists(filepath):
        return filepath
    else:
        return False


@register.filter(name='get_annotation')
def get_annotation(source, name):
    return source.get(name)


@register.simple_tag
def url_replace(request, field, value):
    get_values = request.GET.copy()
    get_values[field] = value
    return get_values.urlencode()


@register.simple_tag
def color_status(status):
    if status == 'ST':
        return 'success'
    elif status == 'HD':
        return 'warning'
    elif status == 'IW':
        return 'info'
    else:
        return 'danger'


@register.simple_tag
def exec_bonus(task, part):
    return round(task.exec_bonus(part), 2)


@register.filter(name='has_group')
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return group in user.groups.all()

#@register.simple_tag
#def is_viewable(task, user):
#    return task.is_viewable(user)
