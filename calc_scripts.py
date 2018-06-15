# -*- coding: utf-8 -*-
# calc_scripts.py
from .models import Task, Execution, IntTask
from django.db.models import Q

def gks(deal, tasks):

    report = '<html><body>Калькуляція по договору {} від {}:<br><br>' \
              .format(deal, deal.date.strftime('%d.%m.%Y'))

    objects = tasks.values('object_code', 'object_address').distinct()

    report += '<table border="1">' \
               '<tr><th>Шифр об’єкту</th><th>Адреса об’єкту</th></tr>'
    for obj in objects:
        report += '<tr><td align="center">{}</td><td>{}</td></tr>' \
                   .format(obj['object_code'], obj['object_address'])
    report += '</table><br>'

    report += '<table border="1"> \
               <tr><th>№ п/п</th><th>Назва об’єкту та вид робіт</th><th>Кількість</th> \
               <th>Ціна, з ПДВ  грн.</th><th>Вартість, з ПДВ грн.</th></tr>'

    project_types = tasks.values('project_type__price_code', 'project_type__description', 'project_type__price') \
                    .order_by('project_type__price_code').distinct()

    index = 0
    svalue = 0
    for ptype in project_types:
        if ptype['project_type__price'] != 0:
            index += 1
            object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code']) \
                                .values_list('object_code', flat=True)
            object_list = ''
            for obj in object_codes:
                object_list += obj + ' '
            count = object_codes.count()
            value = ptype['project_type__price'] * count
            svalue += value
            report += '<tr align="center"> \
                       <td>{}</td><td align="left">{} {}</td><td>{}</td><td>{}</td><td>{}</td> \
                       </tr>' \
                       .format(index, ptype['project_type__description'], object_list,
                               count, ptype['project_type__price'], value)

    wovat = round(svalue / 6 * 5, 2)
    vat = round(svalue / 6, 2)
    report += '<tr align="center"><td colspan="2" rowspan="3">Загальна вартість</td>\
               <td colspan="3">без ПДВ: {} грн. {} коп.</td></tr>\
               <tr align="center"><td colspan="3">ПДВ: {} грн. {} коп.</td></tr>\
               <tr align="center"><td colspan="3">з ПДВ: {} грн. {} коп.</td></tr>' \
               .format(int(wovat), int((wovat - int(wovat)) * 100),
                       int(vat), int((vat - int(vat)) * 100),
                       int(svalue), int((svalue - int(svalue)) * 100))

    report += '</table>'

    return report


def msz(deal, tasks):
    report = '<html><body>Калькуляція по договору {} від {}:<br><br>' \
        .format(deal, deal.date.strftime('%d.%m.%Y'))

    objects = tasks.values('object_code', 'object_address').distinct()

    report += '<table border="1"> \
              <tr><th>Шифр об’єкту</th><th>Адреса об’єкту</th></tr>'
    for obj in objects:
        report += '<tr><td align="center">{}</td><td>{}</td></tr>' \
                  .format(obj['object_code'], obj['object_address'])
    report += '</table><br>'

    report += '<table border="1">\
                               <tr><th>№ п/п</th><th>Найменування робіт</th><th>Однинця виміру</th><th>Кількість</th>\
                               <th>Ціна за одиницю без ПДВ, грн.</th><th>Вартість без ПДВ, грн.</th></tr>'
    obj_index = 0
    swovat = 0
    count = 1
    unit = 'шт.'

    for obj in objects:
        task_index = 0
        obj_index += 1
        object_tasks = tasks.filter(object_code=obj['object_code']) \
                       .values('project_type__price_code', 'project_type__description', 'project_type__price') \
                       .order_by('project_type__price_code')
        report += '<tr align="left"><th colspan="6">{}. {}{}</th></tr>' \
                  .format(obj_index, obj['object_code'], obj['object_address'])

        for task in object_tasks:
            task_index += 1
            wovat = task['project_type__price'] / 6 * 5
            swovat += wovat

            report += '<tr align="center"> \
                      <td>{}.{}</td><td align="left">{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td> \
                      </tr>' \
                      .format(obj_index, task_index, task['project_type__description'],
                      unit, count, round(wovat, 2), round(wovat*count, 2))

    VAT = round(swovat / 6, 2)
    swvat = round(swovat / 5 * 6, 2)
    report += '<tr><td colspan="4" align="right">Загальна вартість без ПДВ:</td><td colspan="2" align="center">{} грн. {} коп.</td></tr> \
              <tr><td colspan="4" align="right">ПДВ 20%:</td><td colspan="2" align="center">{} грн. {} коп.</td></tr> \
              <tr><th colspan="4" align="right">Всього з ПДВ:</th><td colspan="2" align="center">{} грн. {} коп.</td></tr>' \
              .format(int(swovat), int((swovat - int(swovat)) * 100),
                    int(VAT), int((VAT - int(VAT)) * 100),
                    int(swvat), int((swvat - int(swvat)) * 100))

    report += '</table>'

    return report


def bonus_calculation(request, employee, year, month):

    report = '<html><body>Шановний(а) {}.<br><br>'.format(request.user.first_name)

    tasks = Task.objects.filter(owner=employee,
                                exec_status=Task.Sent,
                                actual_finish__month=month,
                                actual_finish__year=year)
    executions = Execution.objects.filter(Q(task__exec_status=Task.Done) | Q(task__exec_status=Task.Sent),
                                          executor=employee,
                                          task__actual_finish__month=month,
                                          task__actual_finish__year=year)
    inttasks = IntTask.objects.filter(executor=employee,
                                      exec_status=IntTask.Done,
                                      actual_finish__month=month,
                                      actual_finish__year=year)

    if tasks.exists() or executions.exists() or inttasks.exists():
        bonuses = 0
        if employee.user == request.user:
            report += 'За {}.{} Вам були нараховані бонуси за виконання проектів та завдань.<br><br>'\
                .format(month, year)
        else:
            report += 'Працівнику {} за {}.{} були нараховані бонуси за виконання проектів та завдань.<br><br>'\
                .format(employee.user.get_full_name(), month, year)

        if tasks.exists():
            index = 0
            report += 'Бонуси за ведення проекту:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Відсоток</th><th>Бонус</th>'

            for task in tasks:
                index += 1
                report += '<tr>\
                           <td>{}</td><td>{}</td><td>{:.80}</td>\
                           <td>{}</td><td>{!s}</td><td>{!s}</td>\
                           </tr>'\
                           .format(index, task.object_code, task.object_address,
                                   task.project_type, task.owner_part(),
                                   round(task.owner_bonus(), 2))
                bonuses += task.owner_bonus()

            report += '</table><br>'

        if executions.exists():
            index = 0
            report += 'Бонуси за виконання проекту:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Шифр об\'єкту</th><th>Адреса об\'єкту</th>\
                       <th>Тип проекту</th><th>Назва робіт</th><th>Відсоток</th><th>Бонус</th>'

            for ex in executions:
                index += 1
                report += '<tr>\
                           <td>{}</td><td>{}</td><td>{:.80}</td>\
                           <td>{}</td><td>{}</td><td>{}</td><td>{!s}</td>\
                           </tr>'\
                           .format(index, ex.task.object_code, ex.task.object_address,
                                   ex.task.project_type, ex.part_name, ex.part,
                                   round(ex.task.exec_bonus(ex.part), 2))
                bonuses += ex.task.exec_bonus(ex.part)

            report += '</table><br>'

        if inttasks.exists():
            index = 0
            report += 'Бонуси за виконання завдань:<br>\
                       <table border="1">\
                       <th>&#8470;</th><th>Завдання</th><th>Бонус</th>'

            for task in inttasks:
                index += 1
                report += '<tr>\
                           <td>{}</td><td>{}</td><td>{}</td>\
                           </tr>'\
                           .format(index, task.task_name, task.bonus)
                bonuses += task.bonus

            report += '</table><br>'

        report += 'Всьго нараховано {} бонусів.</body></html>'.format(round(bonuses, 2))

    else:
        report += 'За {}.{} немає виконаних проектів чи завдань.<br><br>'\
                .format(month, year)

    return report
