from datetime import date
from django.db.models import QuerySet, Manager,F, Max, Func, DateField


class MysqlAddDate(Func):
    function = 'ADDDATE'
    output_field = DateField()

class DealQuerySet(QuerySet):

    def active_deals(self):
        return  self.exclude(act_status='IS') \
                    .exclude(number__icontains='загальний')

    def waiting_for_act(self):
        return  self.exclude(act_status='IS') \
                    .filter(exec_status='ST')

    def overdue_payment(self):
        return  self.annotate(
            pay_date=MysqlAddDate(Max('actofacceptance__date'), F('customer__debtor_term'))
            ).filter(pay_date__lt=date.today(), act_status='IS', pay_status='NP')

    def overdue_execution(self):
        return  self.exclude(exec_status__in=['ST','CL']) \
                    .exclude(expire_date__gte=date.today()) \
                    .exclude(number__icontains='загальний')

    def payment_queue(self):
        return  self.annotate(
            pay_date=MysqlAddDate(Max('actofacceptance__date'), F('customer__debtor_term'))
            ).filter(pay_date__gte=date.today(), act_status='IS', pay_status='NP')
