from django.core.management.base import BaseCommand, CommandError
from planner.models import Task, IntTask, Employee, Execution
from django.conf import settings
from django.core import mail
from datetime import datetime


class Command(BaseCommand):
    help = 'Sending monthly report to employee'

    def handle(self, *args, **options):

        month = datetime.now().month - 1
        year = datetime.now().year

        employees = Employee.objects.exclude(user__username__startswith='outsourcing')
        tasks = Task.objects.filter(exec_status=Task.HaveDone,
                                    actual_finish__month=month,
                                    actual_finish__year=year)
        executions = Execution.objects.filter(task__exec_status=Task.HaveDone,
                                              task__actual_finish__month=month,
                                              task__actual_finish__year=year)
        inttasks = IntTask.objects.filter(exec_status=IntTask.HaveDone,
                                          actual_finish__month=month,
                                          actual_finish__year=year)

        emails = []

        for employee in employees:

            if employee.user.email:
                otasks = tasks.filter(owner=employee)
                eexecutions = executions.filter(executor=employee)
                einttasks = inttasks.filter(executor=employee)

                if otasks.exists() or eexecutions.exists() or einttasks.exists():
                    bonuses = 0
                    message = '<html><body>\
                              Шановний(а) {}.<br><br>\
                              За {}.{} Вам були нараховані бонуси за виконання проектів та завдань.<br>\
                              Звірьте їх будь ласка та при необхідності уточніть інформацію у\
                              свого керівника або відповідальної особи по проекту.<br><br>'\
                              .format(employee.user.first_name, month, year)

                    if otasks.exists():
                        index = 0
                        message += 'Бонуси за ведення проекту:<br>\
                                   <table border="1">\
                                   <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                                   <th>Тип проекту</th><th>Відсоток</th><th>Бонус</th>'

                        for task in otasks:
                            index +=1
                            message += '<tr>\
                                       <td>{}</td><td>{}</td><td>{:.80}</td>\
                                       <td>{}</td><td>{!s}</td><td>{!s}</td>\
                                       </tr>'.\
                                       format(index, task.object_code, task.object_address,
                                              task.project_type, task.owner_part(),
                                              round(task.owner_bonus(), 2))
                            bonuses += task.owner_bonus()

                        message += '</table><br>'

                    if eexecutions.exists():
                        index = 0
                        message += 'Бонуси за виконання проекту:<br>\
                                   <table border="1">\
                                   <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                                   <th>Тип проекту</th><th>Назва робіт</th><th>Відсоток</th><th>Бонус</th>'

                        for ex in eexecutions:
                            index +=1
                            message += '<tr>\
                                       <td>{}</td><td>{}</td><td>{:.80}</td>\
                                       <td>{}</td><td>{}</td><td>{}</td><td>{!s}</td>\
                                       </tr>'.\
                                       format(index, ex.task.object_code, ex.task.object_address,
                                              ex.task.project_type, ex.part_name, ex.part,
                                              round(ex.task.exec_bonus(ex.part), 2))
                            bonuses += ex.task.exec_bonus(ex.part)

                        message += '</table><br>'

                    if einttasks.exists():
                        index = 0
                        message += 'Бонуси за виконання завдань:<br>\
                                   <table border="1">\
                                   <th>&#8470;</th><th>Завдання</th><th>Бонус</th>'

                        for task in einttasks:
                            index +=1
                            message += '<tr>\
                                       <td>{}</td><td>{}</td><td>{}</td>\
                                       </tr>'.\
                                       format(index, task.task_name, task.bonus)
                            bonuses += task.bonus

                        message += '</table><br>'

                    message += 'Всьго Ви отримаєте {} бонусів.</body></html><br>'.format(round(bonuses, 2))

                    emails.append(mail.EmailMessage(
                                  'Бонуси за виконання проектів {}.{}'.format(month, year),
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
