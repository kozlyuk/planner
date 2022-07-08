from decimal import Decimal, ROUND_HALF_UP
from django.utils.html import format_html
from django.conf import settings
from django.db.models import Sum

from planner.models import ActOfAcceptance, Deal, Payment, Task

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


def act_list_context(company, customer, from_date, to_date):

    # get acts
    acts = ActOfAcceptance.objects.filter(deal__company=company,
                                          deal__customer=customer
                                          )
    if from_date:
        acts = acts.filter(date__gte=from_date)
    if to_date:
        acts = acts.filter(date__lte=to_date)

    # prepare table data
    labels = ["№",
              ActOfAcceptance._meta.get_field('deal').verbose_name,
              ActOfAcceptance._meta.get_field('number').verbose_name,
              ActOfAcceptance._meta.get_field('value').verbose_name,
              ActOfAcceptance._meta.get_field('date').verbose_name,
              ]
    index = 0
    svalue = Decimal(0)
    act_list = []
    for act in acts:
        index += 1
        svalue += act.value
        act_list.append([index,
                         format_html('<a href="%s%s">%s</a>'
                                     % (settings.SITE_URL,
                                        act.deal.get_absolute_url(),
                                        act.deal.number)),
                         act.number,
                         act.value,
                         act.date
                         ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'act_list': act_list,
        'svalue': svalue
    }
    return context


def payment_list_context(company, customer, from_date, to_date):

    # get payments
    payments = Payment.objects.filter(deal__company=company,
                                      deal__customer=customer
                                      )
    if from_date:
        payments = payments.filter(date__gte=from_date)
    if to_date:
        payments = payments.filter(date__lte=to_date)

    # prepare table data
    labels = ["№",
              Payment._meta.get_field('deal').verbose_name,
              Payment._meta.get_field('act_of_acceptance').verbose_name,
              Payment._meta.get_field('value').verbose_name,
              Payment._meta.get_field('date').verbose_name,
              ]
    index = 0
    svalue = Decimal(0)
    payment_list = []
    for payment in payments:
        index += 1
        svalue += payment.value
        payment_list.append([index,
                         format_html('<a href="%s%s">%s</a>'
                                     % (settings.SITE_URL,
                                        payment.deal.get_absolute_url(),
                                        payment.deal.number)),
                         payment.act_of_acceptance,
                         payment.value,
                         payment.date
                         ])
    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'payment_list': payment_list,
        'svalue': svalue
    }
    return context


def customer_report_context(company, customer, from_date, to_date):

    # prepare context data
    acts = ActOfAcceptance.objects.filter(deal__company=company,
                                          deal__customer=customer
                                          )
    payments = Payment.objects.filter(deal__company=company,
                                      deal__customer=customer
                                      )
    work_done = Task.objects.filter(deal__company=company,
                                    deal__customer=customer
                                    )

    acts_sum = acts.aggregate(Sum('value'))['value__sum'] or 0
    payments_sum = payments.aggregate(Sum('value'))['value__sum'] or 0
    receivables = acts_sum - payments_sum

    if from_date:
        acts = acts.filter(date__gte=from_date)
        payments = payments.filter(date__gte=from_date)
        work_done = work_done.filter(actual_finish__gte=from_date)
    if to_date:
        acts = acts.filter(date__lte=to_date)
        payments = payments.filter(date__lte=to_date)
        work_done = work_done.filter(actual_finish__lte=to_date)

    acts_for_period = acts.aggregate(Sum('value'))['value__sum'] or 0
    payments_for_period = payments.aggregate(Sum('value'))['value__sum'] or 0
    work_done_for_period = work_done.aggregate(Sum('project_type__price'))['project_type__price__sum'] or 0

    # prepare table data
    labels = ['Дебіторська заборгованість',
              'Виписано актів',
              'Оплачено',
              'Виконано робіт',
              ]

    report_data = [receivables,
                   acts_for_period,
                   payments_for_period,
                   work_done_for_period
                   ]

    # creating context
    context = {
        'company': company,
        'customer': customer,
        'labels': labels,
        'report_data': report_data,
    }
    return context
