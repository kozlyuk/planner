from decimal import Decimal, ROUND_HALF_UP
from django.utils.html import format_html
from django.conf import settings

from planner.models import Deal

from .models import Report

def receivables_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.receivables().filter(company=company,
                                              customer=customer,
                                              )
    if from_date:
        deals = deals.filter(date__gte=from_date)
    if to_date:
        deals = deals.filter(date__lte=to_date)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
              Deal._meta.get_field('date').verbose_name,
              ]
    index = 0
    svalue = Decimal(0)
    deal_list = []
    for deal in deals:
        index += 1
        acts_total = deal.acts_total()
        paid_total = deal.paid_total()
        if acts_total > paid_total:
            svalue += acts_total - paid_total

        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.get_exec_status_display(),
                          deal.date
                          ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context


def waiting_for_act_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.waiting_for_act().filter(company=company,
                                                  customer=customer,
                                                  )
    if from_date:
        deals = deals.filter(date__gte=from_date)
    if to_date:
        deals = deals.filter(date__lte=to_date)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
              Deal._meta.get_field('date').verbose_name,
              ]
    index = 0
    svalue = Decimal(0)
    deal_list = []
    for deal in deals:
        index += 1
        acts_total = deal.acts_total()
        paid_total = deal.paid_total()
        if acts_total > paid_total:
            svalue += acts_total - paid_total

        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.get_exec_status_display(),
                          deal.date
                          ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context


def payment_queue_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.payment_queue().filter(company=company,
                                                customer=customer,
                                                )
    if from_date:
        deals = deals.filter(pay_date__gte=from_date)
    if to_date:
        deals = deals.filter(pay_date__lte=to_date)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              "Планова дата оплати",
              ]
    index = 0
    svalue = Decimal(0)
    deal_list = []
    for deal in deals:
        index += 1
        acts_total = deal.acts_total()
        paid_total = deal.paid_total()
        if acts_total > paid_total:
            svalue += acts_total - paid_total

        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.pay_date_calc()
                          ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context


def overdue_payment_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.overdue_payment().filter(company=company,
                                                  customer=customer,
                                                  )
    if from_date:
        deals = deals.filter(pay_date__gte=from_date)
    if to_date:
        deals = deals.filter(pay_date__lte=to_date)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              "Планова дата оплати",
              ]
    index = 0
    svalue = Decimal(0)
    deal_list = []
    for deal in deals:
        index += 1
        acts_total = deal.acts_total()
        paid_total = deal.paid_total()
        if acts_total > paid_total:
            svalue += acts_total - paid_total

        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.pay_date_calc()
                          ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context


def overdue_execution_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.overdue_execution().filter(company=company,
                                                    customer=customer,
                                                    )
    if from_date:
        deals = deals.filter(expire_date__gte=from_date)
    if to_date:
        deals = deals.filter(expire_date__lte=to_date)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
              Deal._meta.get_field('expire_date').verbose_name,
              ]
    index = 0
    svalue = Decimal(0)
    deal_list = []
    for deal in deals:
        index += 1
        acts_total = deal.acts_total()
        paid_total = deal.paid_total()
        if acts_total > paid_total:
            svalue += acts_total - paid_total

        deal_list.append([index,
                          format_html('<a href="%s%s">%s</a>'
                                      % (settings.SITE_URL,
                                         deal.get_absolute_url(),
                                         deal.number)),
                          deal.value,
                          deal.get_pay_status_display(),
                          deal.get_act_status_display(),
                          deal.get_exec_status_display(),
                          deal.expire_date
                          ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context

def context_report_render(report, customer, company=None, from_date=None, to_date=None):
    """ return context defined in report.context """

    return globals()[report.context](company, customer, from_date, to_date)