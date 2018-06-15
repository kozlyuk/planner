# -*- coding: utf-8 -*-
# calc_scripts.py

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
