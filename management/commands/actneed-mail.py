from django.core.management.base import BaseCommand, CommandError
from planner.models import Deal, Employee
from django.conf import settings
from django.core import mail


class Command(BaseCommand):
    help = 'Sending notifications about closed contracts to accountants'

    def handle(self, *args, **options):

        accountants = Employee.objects.filter(user__groups__name__in=['Бухгалтери'])
        deals = Deal.objects.exclude(act_status=Deal.Issued)

        emails = []
        completed = []

        for deal in deals:
            if deal.exec_status() == 'Виконано' and 'загальний' not in deal.number:
                completed.append(deal)

        for accountant in accountants:

            if completed and accountant.user.email:
                index = 0
                message = '<html><body>\
                           Шановна(ий) {}.<br><br>\
                           Є виконані угоди які чекають закриття акту виконаних робіт:<br>\
                           <table border="1">\
                           <th>&#8470;</th><th>Номер договору</th><th>Замовник</th>\
                           <th>Вартість робіт</th><th>Статус оплати</th><th>Акт виконаних робіт</th>'\
                           .format(accountant.user.first_name)

                for deal in completed:
                    index += 1
                    message += '<tr>\
                               <td>{}</td>\
                               <td><a href="http://erp.itel.rv.ua/admin/planner/deal/{}/change/">{}</a></td>\
                               <td>{}</td>\
                               <td>{}</td>\
                               <td>{!s}</td>\
                               <td>{!s}</td>\
                               </tr>'\
                               .format(index, deal.pk, deal.number, deal.customer,
                                       deal.value, deal.get_pay_status_display(), deal.get_act_status_display())

                message += '</table></body></html><br>'

                emails.append(mail.EmailMessage(
                              'Угоди які чекають закриття акту',
                              message,
                              settings.DEFAULT_FROM_EMAIL,
                              [accountant.user.email],
                ))

        for email in emails:
            email.content_subtype = "html"

        connection = mail.get_connection()
        connection.open()
        connection.send_messages(emails)
        connection.close()
