from planner.models import Deal, Task, Execution, IntTask, Employee
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test


@login_required()
@user_passes_test(lambda u: u.groups.filter(name='Бухгалтери').exists())
def calculation(request, deal_id):

    deal = Deal.objects.get(id=deal_id)
    tasks = Task.objects.filter(deal=deal)

    if tasks.exists():

        message = '<html><body>Калькуляція по договору {} від {}:<br><br>'\
                  .format(deal, deal.creation_date.strftime('%d.%m.%Y'))

        objects = tasks.values('object_code', 'object_address').distinct()

        message += '<table border="1">\
                   <th>Шифр об’єкту</th><th>Адреса об’єкту</th>'
        for obj in objects:
            message += '<tr>\
                       <td align="center">{}</td><td>{}</td>\
                       </tr>'\
                       .format(obj['object_code'], obj['object_address'])
        message += '</table><br>'

        message += '<table border="1">\
                   <th>№ п/п</th><th>Назва об’єкту та вид робіт</th><th>Кількість</th>\
                   <th>Ціна, з ПДВ  грн.</th><th>Вартість, з ПДВ грн.</th>'

        project_types = tasks.values('project_type__price_code', 'project_type__description', 'project_type__price')\
                             .order_by('project_type__price_code').distinct()

        index = 0
        svalue = 0
        for ptype in project_types:
            if ptype['project_type__price'] != 0:
                index += 1
                object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code'])\
                    .values_list('object_code', flat=True)
                object_list = ''
                for obj in object_codes:
                    object_list += obj + ' '
                count = object_codes.count()
                value = ptype['project_type__price'] * count
                svalue += value
                message += '<tr align="center">\
                       <td>{}</td><td align="left">{} {}</td><td>{}</td><td>{}</td><td>{}</td>\
                       </tr>'\
                       .format(index, ptype['project_type__description'], object_list,
                              count, ptype['project_type__price'], value)

        woVAT = round(svalue/6*5, 2)
        VAT = round(svalue/6, 2)
        message += '<tr align="center"><td colspan="2" rowspan="3">Загальна вартість</td>\
                   <td colspan="3">без ПДВ: {} грн. {} коп.</td></tr>\
                   <tr align="center"><td colspan="3">ПДВ: {} грн. {} коп.</td></tr>\
                   <tr align="center"><td colspan="3">з ПДВ: {} грн. {} коп.</td></tr>'\
                   .format(int(woVAT), int((woVAT - int(woVAT))*100),
                           int(VAT), int((VAT - int(VAT))*100),
                           int(svalue), int((svalue - int(svalue))*100))

        message += '</table>'

    return HttpResponse(message)


@login_required()
def bonus_calc(request, employee_id, year, month):

    employee = Employee.objects.get(id=employee_id)
    message = '<html><body>Шановний(а) {}.<br><br>'.format(request.user.first_name)
    if not request.user.is_superuser and request.user != employee.user and request.user != employee.head.user:
        message += 'Ви не маєте доступу до даних цього користувача.</body></html>'
        return HttpResponse(message)

    tasks = Task.objects.filter(owner=employee,
                                exec_status=Task.Done,
                                actual_finish__month=month,
                                actual_finish__year=year)
    executions = Execution.objects.filter(executor=employee,
                                          task__exec_status=Task.Done,
                                          task__actual_finish__month=month,
                                          task__actual_finish__year=year)
    inttasks = IntTask.objects.filter(executor=employee,
                                      exec_status=IntTask.Done,
                                      actual_finish__month=month,
                                      actual_finish__year=year)

    if tasks.exists() or executions.exists() or inttasks.exists():
        bonuses = 0
        if employee.user == request.user:
            message += 'За {}.{} Вам були нараховані бонуси за виконання проектів та завдань.<br><br>'\
                .format(month, year)
        else:
            message += 'Працівнику {} за {}.{} були нараховані бонуси за виконання проектів та завдань.<br><br>'\
                .format(employee.user.get_full_name(), month, year)

        if tasks.exists():
            index = 0
            message += 'Бонуси за ведення проекту:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Відсоток</th><th>Бонус</th>'

            for task in tasks:
                index += 1
                message += '<tr>\
                           <td>{}</td><td>{}</td><td>{:.80}</td>\
                           <td>{}</td><td>{!s}</td><td>{!s}</td>\
                           </tr>'\
                           .format(index, task.object_code, task.object_address,
                                   task.project_type, task.owner_part(),
                                   round(task.owner_bonus(), 2))
                bonuses += task.owner_bonus()

            message += '</table><br>'

        if executions.exists():
            index = 0
            message += 'Бонуси за виконання проекту:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Назва робіт</th><th>Відсоток</th><th>Бонус</th>'

            for ex in executions:
                index += 1
                message += '<tr>\
                           <td>{}</td><td>{}</td><td>{:.80}</td>\
                           <td>{}</td><td>{}</td><td>{}</td><td>{!s}</td>\
                           </tr>'\
                           .format(index, ex.task.object_code, ex.task.object_address,
                                   ex.task.project_type, ex.part_name, ex.part,
                                   round(ex.task.exec_bonus(ex.part), 2))
                bonuses += ex.task.exec_bonus(ex.part)

            message += '</table><br>'

        if inttasks.exists():
            index = 0
            message += 'Бонуси за виконання завдань:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Завдання</th><th>Бонус</th>'

            for task in inttasks:
                index += 1
                message += '<tr>\
                           <td>{}</td><td>{}</td><td>{}</td>\
                           </tr>'\
                           .format(index, task.task_name, task.bonus)
                bonuses += task.bonus

            message += '</table><br>'

        message += 'Всьго нараховано {} бонусів.</body></html>'.format(round(bonuses, 2))
        return HttpResponse(message)
    else:
        message += 'Відсутні виконані проекти чи завдання.</body></html>'
        return HttpResponse(message)