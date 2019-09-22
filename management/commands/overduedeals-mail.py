from django.core.management.base import BaseCommand, CommandError
from planner.models import Deal, Employee
from django.conf import settings
from django.core import mail
from datetime import date


class Command(BaseCommand):
    help = 'Sending notifications about debtors to accountants'

    def handle(self, *args, **options):

        pms = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
        deals = Deal.objects.exclude(expire_date__gte=date.today()) \
                            .exclude(number__icontains='загальний') \
                            .exclude(number__icontains='злетіли')

        emails = []
        overdue = []

        for deal in deals:
            if deal.exec_status() != 'Надіслано':   # todo make filter by exec_status
                overdue.append(deal)


        for pm in pms:

            if overdue and pm.user.email:
                index = 0
                message = '<html><body>\
                           Шановна(ий) {}.<br><br>\
                           Маємо такі протерміновані угоди:<br>\
                           <table border="1">\
                           <th>&#8470;</th><th>Номер договору</th><th>Замовник</th>\
                           <th>Вартість робіт</th><th>Статус оплати</th>\
                           <th>Акт виконаних робіт</th><th>Дата закінчення договору</th>\
                           <th>Статус виконання</th>'\
                           .format(pm.user.first_name)

                for deal in overdue:
                    index += 1
                    message += '<tr>\
                               <td>{}</td>\
                               <td><a href="http://erp.itel.rv.ua/deal/{}/change/">{}</a></td>\
                               <td>{}</td>\
                               <td>{}</td>\
                               <td>{!s}</td>\
                               <td>{!s}</td>\
                               <td>{!s}</td>\
                               <td>{}</td>\
                               </tr>'\
                               .format(index, deal.pk, deal.number, deal.customer,
                                       deal.value, deal.get_pay_status_display(),
                                       deal.get_act_status_display(), deal.expire_date,
                                       deal.exec_status())  # todo make filter by exec_status

                message += '</table></body></html><br>'

                emails.append(mail.EmailMessage(
                              'Протерміновані угоди',
                              message,
                              settings.DEFAULT_FROM_EMAIL,
                              [pm.user.email],
                ))

        for email in emails:
            email.content_subtype = "html"

        connection = mail.get_connection()
        connection.open()
        connection.send_messages(emails)
        connection.close()
