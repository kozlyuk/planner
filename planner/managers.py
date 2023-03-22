from datetime import date
from django.db.models import QuerySet, Sum, F, Max, Func, DateField, DecimalField
from django.db.models.functions import Coalesce


class MysqlAddDate(Func):
    function = 'ADDDATE'
    output_field = DateField()

class DealQuerySet(QuerySet):

    def active_deals(self):
        return  self.exclude(exec_status='CL') \
                    .exclude(act_status='IS') \

    def waiting_for_act(self):
        return  self.exclude(act_status='IS') \
                    .filter(exec_status='ST') \
                    .order_by('expire_date')

    def overdue_payment(self):
        return  self.annotate(pay_date=MysqlAddDate(Max('actofacceptance__date'), F('customer__debtor_term'))) \
                    .filter(pay_date__lt=date.today(), act_status='IS', pay_status='NP') \
                    .order_by('pay_date')

    def overdue_execution(self):
        return  self.exclude(exec_status__in=['ST','CL']) \
                    .exclude(expire_date__gte=date.today()) \
                    .order_by('expire_date')

    def payment_queue(self):
        return  self.annotate(pay_date=MysqlAddDate(Max('actofacceptance__date'), F('customer__debtor_term'))) \
                    .filter(pay_date__gte=date.today(), act_status='IS', pay_status='NP') \
                    .order_by('pay_date')

    def receivables(self):
        return  self.exclude(act_status='NI') \
                    .exclude(pay_status__in=['PU', 'AP']) \
                    .exclude(exec_status='CL') \
                    .annotate(acts_total=Coalesce(Sum('actofacceptance__value'), 0, output_field=DecimalField()),
                              paid_total=Coalesce(Sum('payment__value'), 0, output_field=DecimalField())) \
                    .annotate(debt=F('acts_total')-F('paid_total')) \
                    .order_by('expire_date')


class ActQuerySet(QuerySet):

    def receivables(self):
        return  self.exclude(deal__act_status='NI') \
                    .exclude(deal__pay_status='AP') \
                    .annotate(acts_total=Coalesce(Sum('deal__actofacceptance__value'), 0, output_field=DecimalField()))


class PaymentQuerySet(QuerySet):

    def receivables(self):
        return  self.exclude(deal__pay_status__in=['NP', 'AP']) \
                    .annotate(paid_total=Coalesce(Sum('deal__payment__value'), 0, output_field=DecimalField()))
