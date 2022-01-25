from decimal import Decimal, ROUND_HALF_UP
from django.utils.html import format_html
from django.conf import settings

from planner.models import Deal

from .models import Report

def receivables_context(company, customer, from_date, to_date):

    # get deals
    deals = Deal.objects.receivables().filter(customer=customer)

    # prepare table data
    labels = ["№",
              Deal._meta.get_field('number').verbose_name,
              Deal._meta.get_field('value').verbose_name,
              Deal._meta.get_field('pay_status').verbose_name,
              Deal._meta.get_field('act_status').verbose_name,
              Deal._meta.get_field('exec_status').verbose_name,
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
                          deal.get_exec_status_display()
                          ])
    # creating context
    context = {
        'customer': customer,
        'labels': labels,
        'deal_list': deal_list,
        'svalue': svalue
    }
    return context



def context_report_render(report, customer, company=None, from_date=None, to_date=None):
    """ return context defined in report.context """

    return globals()[report.context](company, customer, from_date, to_date)
