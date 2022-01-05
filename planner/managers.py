from datetime import date
from django.db.models import QuerySet, Manager,F, Max, Func, DateField


class MysqlAddDate(Func):
    function = 'ADDDATE'
    output_field = DateField()

class DealQuerySet(QuerySet):
    def overdue_payment(self):
        return  self.annotate(
            pay_date=MysqlAddDate(Max('actofacceptance__date'), F('customer__debtor_term'))
            ).filter(pay_date__lt=date.today(), act_status='IS', pay_status='NP')
