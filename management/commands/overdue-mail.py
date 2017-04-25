from django.core.management.base import BaseCommand, CommandError
from planner.models import Task, Employee
from django.conf import settings
from django.core import mail
from datetime import date


class Command(BaseCommand):
    help = 'Sending notifications to tasks owners and executors'

    def handle(self, *args, **options):

        employees = Employee.objects.exclude(user__username__startswith='outsourcing')
        tasks = Task.objects.exclude(exec_status=Task.Done).\
                             exclude(deal__expire_date__gte=date.today(),
                                     planned_finish__isnull=True).\
                             exclude(deal__expire_date__gte=date.today(),
                                     planned_finish__gte=date.today())

        emails = []

        for employee in employees:
            otasks = tasks.filter(owner=employee)
            etasks = tasks.filter(executors__in=[employee])

            message = '<html><body>Шановний(а) {}.<br><br>'\
                      .format(employee.user.first_name)

            if otasks.exists() and employee.user.email:
                index = 0
                message += 'Протерміновані наступні проекти, в яких Ви відповідальна особа:<br>\
                           <table border="1">\
                           <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                           <th>Тип проекту</th><th>Статус</th><th>Попередження</th>'

                for task in otasks:
                    index +=1
                    message += '<tr>\
                               <td>{}</td><td>{}</td><td>{:.80}</td>\
                               <td>{}</td><td>{!s}</td><td>{!s}</td>\
                               </tr>'.\
                               format(index, task.object_code, task.object_address,
                                      task.project_type, task.get_exec_status_display(),
                                      task.overdue_status())

                message += '</table><br>'

            if etasks.exists() and employee.user.email:
                index = 0
                message += 'Протерміновані наступні проекти, в яких Ви виконуєте роботи:<br>\
                           <table border="1">\
                           <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                           <th>Тип проекту</th><th>Статус</th><th>Попередження</th>'

                for task in etasks:
                    index +=1
                    message += '<tr>\
                               <td>{}</td><td>{}</td><td>{:.80}</td>\
                               <td>{}</td><td>{!s}</td><td>{!s}</td>\
                               </tr>'\
                               .format(index, task.object_code, task.object_address,
                                       task.project_type, task.get_exec_status_display(),
                                       task.overdue_status())

                message += '</table></body></html><br>'

            if employee.user.email and (otasks.exists() or etasks.exists()):
                emails.append(mail.EmailMessage(
                              'Протерміновані проекти',
                              message,
                              settings.DEFAULT_FROM_EMAIL,
                              [employee.user.email],
                              ['s.kozlyuk@itel.rv.ua'],
                ))

        for email in emails:
            email.content_subtype = "html"

        connection = mail.get_connection()
        connection.open()
        connection.send_messages(emails)
        connection.close()
