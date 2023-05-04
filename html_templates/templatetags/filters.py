from django import template
from decimal import Decimal, ROUND_HALF_UP

from ..number_to_text import num2text, decimal2text

register = template.Library()


def get_main_units(units):
    if units == 'hrn':
        return ((u'гривня', u'гривні', u'гривень'), 'f')
    if units == 'calendar_days':
        return ((u'календарний день', u'календарних дні', u'календарних днів'), 'm')
    return ((u'', u'', u''), 'm')

def get_int_units(units):
    if units == 'hrn':
        return ((u'гривня', u'гривні', u'гривень'), 'f')
    return ((u'', u'', u''), 'm')

def get_exp_units(units):
    if units == 'hrn':
        return ((u'копійка', u'копійки', u'копійок'), 'f')
    return ((u'', u'', u''), 'm')


@register.simple_tag
def num_to_text(value, units):
    return num2text(int(value), get_main_units(units))


@register.simple_tag
def decimal_to_text(value, units):
    return decimal2text(value, 2, get_int_units(units), get_exp_units(units))


@register.filter
def exp_part(value):
    return str((value - int(value)))[2:]


@register.filter
def quantize(value):
    return value.quantize(Decimal("1.00"), ROUND_HALF_UP)


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
    if option == 'vat_without_currency':
        if summary_value is None or summary_value == 0:
            return '0.00'
        summary_value = round(summary_value / 5, 2)
        summary_value = str(summary_value).split('.')
        return summary_value[0] + ',' + summary_value[1]


@register.filter
def VAT(value):
    return quantize(value / 6)

@register.filter
def VAT5(value):
    return quantize(value / 5)

@register.filter
def without_VAT(value):
    return quantize(value / Decimal(1.2))


@register.filter
def add_VAT(value):
    return quantize(value * Decimal(1.2))


@register.simple_tag
def calc_vat(value, option='without_currency'):
    '''
    with_currency return * грн. ** коп.
    without_currency return *.**.
    where * is the value
    '''
    if option == 'with_currency':
        if value is None or value == 0:
            return '0 грн. 00 коп.'
        vat = quantize(value * Decimal(1.2))
        vat = str(vat).split('.')
        return vat[0] + ' грн. ' + vat[1] + ' коп.'
    if option == 'without_currency':
        if value is None or value == 0:
            return '0.00'
        return quantize(value * Decimal(1.2))
    return value
