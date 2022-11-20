from datetime import date
from django.utils.formats import date_format
from decimal import Decimal, ROUND_HALF_UP
from django.utils.html import format_html
from django.conf import settings
from django.db.models import Sum

from planner.models import ActOfAcceptance, Deal, Payment, Task, Customer

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


def context_chart_render(chart, year, customers=None):
    """ return context defined in chart.context """

    return globals()[chart.context](year, customers)


def fin_analysis_context(year, customers):

    # prepare chart data
    xAxis = []
    acts_data = []
    payments_data = []
    work_done_data = []
    receivables_data = []
    stock_data = []
    turnover_closed_data = []
    turnover_data = []

    for month in range(12):
        xAxis.append(date_format(date.today().replace(month=month+1), 'M'))

    for customer in customers:
        acts_income_list = []
        payments_income_list = []
        work_done_list = []
        receivables_list = []
        stock_list = []

        for month in range(12):
            acts_customer = ActOfAcceptance.objects.filter(deal__customer=customer)
            payments_customer = Payment.objects.filter(deal__customer=customer)
            acts_income = acts_customer.filter(date__year=year,
                                               date__month=month+1) \
                                       .aggregate(Sum('value'))['value__sum'] or 0
            acts_income_list.append(float(acts_income))
            payments_income = payments_customer.filter(date__year=year,
                                                       date__month=month+1) \
                                               .aggregate(Sum('value'))['value__sum'] or 0
            payments_income_list.append(float(payments_income))
            work_done_income = Task.objects.filter(deal__customer=customer,
                                                   actual_finish__year=year,
                                                   actual_finish__month=month+1) \
                                            .aggregate(Sum('project_type__price'))['project_type__price__sum'] or 0
            work_done_list.append(float(work_done_income))
            acts_sum = acts_customer.filter(date__year__lt=year) \
                                    .aggregate(Sum('value'))['value__sum'] or 0
            payments_sum = payments_customer.filter(date__year__lt=year) \
                                            .aggregate(Sum('value'))['value__sum'] or 0
            receivables_list.append(float(acts_sum - payments_sum + acts_income - payments_income))
            stock_list.append(float(work_done_income-acts_income))

        acts_data.append({"name": customer.name,
                          "data": acts_income_list})
        payments_data.append({"name": customer.name,
                              "data": payments_income_list})
        work_done_data.append({"name": customer.name,
                               "data": work_done_list})
        receivables_data.append({"name": customer.name,
                                 "data": receivables_list})
        stock_data.append({"name": customer.name,
                           "data": stock_list})
        turnover_closed_data.append({"name": customer.name,
                                     "y": sum(acts_income_list)})
        turnover_data.append({"name": customer.name,
                              "y": sum(work_done_list)})

    # creating context
    context = {
        'customers': customers,
        'xAxis': xAxis,
        'acts_data': acts_data,
        'payments_data': payments_data,
        'work_done_data': work_done_data,
        'receivables_data': receivables_data,
        'stock_data': stock_data,
        'turnover_closed_data': turnover_closed_data,
        'turnover_data': turnover_data
    }
    return context


def customer_fin_analysis_context(year, customers):

    # prepare chart data
    customer = customers.first()
    xAxis = []
    series = []

    for month in range(12):
        xAxis.append(date_format(date.today().replace(month=month+1), 'M'))

    acts_income_list = []
    payments_income_list = []
    work_done_list = []
    receivables_list = []
    stock_list = []

    for month in range(12):
        acts_customer = ActOfAcceptance.objects.filter(deal__customer=customer)
        payments_customer = Payment.objects.filter(deal__customer=customer)

        acts_income = acts_customer.filter(date__year=year,
                                            date__month=month+1) \
                                    .aggregate(Sum('value'))['value__sum'] or 0
        acts_income_list.append(float(acts_income))

        payments_income = payments_customer.filter(date__year=year,
                                                    date__month=month+1) \
                                            .aggregate(Sum('value'))['value__sum'] or 0
        payments_income_list.append(float(payments_income))

        work_done_income = Task.objects.filter(deal__customer=customer,
                                                actual_finish__year=year,
                                                actual_finish__month=month+1) \
                                        .aggregate(Sum('project_type__price'))['project_type__price__sum'] or 0
        work_done_list.append(float(work_done_income))

        acts_sum = acts_customer.filter(date__year__lt=year) \
                                .aggregate(Sum('value'))['value__sum'] or 0
        payments_sum = payments_customer.filter(date__year__lt=year) \
                                        .aggregate(Sum('value'))['value__sum'] or 0
        receivables_list.append(float(acts_sum - payments_sum + acts_income - payments_income))
        stock_list.append(float(work_done_income-acts_income))

    series.append({"name": "Дохід по актам", "data": acts_income_list})
    series.append({"name": "Оплачено", "data": payments_income_list})
    series.append({"name": "Виконано робіт", "data": work_done_list})
    series.append({"name": "Дебіторська заборгованість", "data": receivables_list})
    series.append({"name": "Рівень запасів", "data": stock_list})

    # creating context
    context = {
        'customer': customer,
        'xAxis': xAxis,
        'series': series,
    }
    return context


def income_structure_context(year, customers):

    # prepare chart data
    xAxis = []
    acts_data = []
    payments_data = []
    work_done_data = []
    receivables_data = []
    stock_data = []

    for month in range(12):
        xAxis.append(date_format(date.today().replace(month=month+1), 'M'))

    if not customers:
        customer_ids = list(set(ActOfAcceptance.objects.filter(date__year=year).values_list('deal__customer', flat=True)))
        customers = Customer.objects.filter(pk__in=customer_ids)

    for customer in customers:
        acts_customer = ActOfAcceptance.objects.filter(deal__customer=customer)
        payments_customer = Payment.objects.filter(deal__customer=customer)

        acts_income = acts_customer.filter(date__year=year) \
                                   .aggregate(Sum('value'))['value__sum'] or 0
        if acts_income > 0:
            acts_data.append({"name": customer.name,
                              "y": float(acts_income)})

        work_done_income = Task.objects.filter(deal__customer=customer,
                                               actual_finish__year=year) \
                                       .aggregate(Sum('project_type__price'))['project_type__price__sum'] or 0
        if work_done_income > 0:
            work_done_data.append({"name": customer.name,
                                   "y": float(work_done_income)})

        payments_income = payments_customer.filter(date__year=year) \
                                   .aggregate(Sum('value'))['value__sum'] or 0
        if payments_income > 0:
            payments_data.append({"name": customer.name,
                                  "y": float(payments_income)})

        acts_sum = ActOfAcceptance.objects.filter(deal__customer=customer,
                                                    date__year__lte=year) \
                                            .aggregate(Sum('value'))['value__sum'] or 0

        payments_sum = Payment.objects.filter(deal__customer=customer,
                                                date__year__lte=year) \
                                        .aggregate(Sum('value'))['value__sum'] or 0
        receivables = acts_sum - payments_sum
        if receivables > 0:
            receivables_data.append({"name": customer.name,
                                     "y": float(receivables)})
        stocks = work_done_income-acts_income
        if stocks > 0:
            stock_data.append({"name": customer.name,
                               "y": float(stocks)})

    # creating context
    context = {
        'customers': customers,
        'acts_data': acts_data,
        'work_done_data': work_done_data,
        'payments_data': payments_data,
        'receivables_data': receivables_data,
        'stock_data': stock_data,
    }
    return context
