from django import template
from django.conf.locale.uk import formats as uk_formats

from ..number_to_text import num2text, decimal2text

register = template.Library()


def get_main_units(units):
    if units == 'calendar_days':
        return ((u'календарний день', u'календарних дня', u'календарних днів'), 'm')
    return ((u'', u'', u''), 'm')

def get_int_units(units):
    if units == 'hrn':
        return ((u'гривня', u'гривні', u'гривень'), 'f')
    return ((u'', u'', u''), 'm')

def get_exp_units(units):
    if units == 'hrn':
        return ((u'копійка', u'копійки', u'копійок'), 'f')
    return ((u'', u'', u''), 'm')


@register.filter
def VAT(value):
    return round(value/6, 2)


@register.simple_tag
def num_to_text(value, units):
    return num2text(value, get_main_units(units))


@register.simple_tag
def decimal_to_text(value, units):
    return decimal2text(value, 2, get_int_units(units), get_exp_units(units))

@register.simple_tag
def calc_summary(summary_value, option='without_currency'):
    '''
    with_currency return * грн. ** коп.
    without_currency return *.**.
    where * is the value
    '''
    if option == 'with_currency':
        if summary_value is None or summary_value == 0:
            return '0 грн. 0 коп.'
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ' грн. ' + summary_value[1] + ' коп.'
    if option == 'without_currency':
        if summary_value is None or summary_value == 0:
            return '0.00'
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ',' + summary_value[1]
    if option == 'vat_with_currency':
        if summary_value is None or summary_value == 0:
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
        if value is None or value == 0:
            return '0 грн. 00 коп.'
        vat = round(value + value / 5, 2)
        vat = str(vat).split('.')
        return vat[0] + ' грн. ' + vat[1] + ' коп.'
    if option == 'without_currency':
        if value is None or value == 0:
            return '0.00'
        vat = round(value + value / 5, 2)
        vat = str(vat).split('.')
        return vat[0] + ',' + vat[1]
    return value
