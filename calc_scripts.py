# -*- coding: utf-8 -*-
# calc_scripts.py

def gks(deal, tasks):

    message = '<html><body>Калькуляція по договору {} від {}:<br><br>' \
              .format(deal, deal.date.strftime('%d.%m.%Y'))

    objects = tasks.values('object_code', 'object_address').distinct()

    message += '<table border="1">\
                           <th>Шифр об’єкту</th><th>Адреса об’єкту</th>'
    for obj in objects:
        message += '<tr>\
                               <td align="center">{}</td><td>{}</td>\
                               </tr>' \
            .format(obj['object_code'], obj['object_address'])
    message += '</table><br>'

    message += '<table border="1">\
                           <th>№ п/п</th><th>Назва об’єкту та вид робіт</th><th>Кількість</th>\
                           <th>Ціна, з ПДВ  грн.</th><th>Вартість, з ПДВ грн.</th>'

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
            message += '<tr align="center">\
                               <td>{}</td><td align="left">{} {}</td><td>{}</td><td>{}</td><td>{}</td>\
                               </tr>' \
                .format(index, ptype['project_type__description'], object_list,
                        count, ptype['project_type__price'], value)

    woVAT = round(svalue / 6 * 5, 2)
    VAT = round(svalue / 6, 2)
    message += '<tr align="center"><td colspan="2" rowspan="3">Загальна вартість</td>\
                           <td colspan="3">без ПДВ: {} грн. {} коп.</td></tr>\
                           <tr align="center"><td colspan="3">ПДВ: {} грн. {} коп.</td></tr>\
                           <tr align="center"><td colspan="3">з ПДВ: {} грн. {} коп.</td></tr>' \
        .format(int(woVAT), int((woVAT - int(woVAT)) * 100),
                int(VAT), int((VAT - int(VAT)) * 100),
                int(svalue), int((svalue - int(svalue)) * 100))

    message += '</table>'

    return message


def msz  (deal, tasks):

    message = '<html><body>Калькуляція по договору {} від {}:<br><br>' \
        .format(deal, deal.date.strftime('%d.%m.%Y'))

    objects = tasks.values('object_code', 'object_address').distinct()

    message += '<table border="1">\
                               <th>№ п/п</th><th>Найменування робіт</th><th>Однинця виміру</th><th>Кількість</th>\
                               <th>Ціна за одиницю без ПДВ, грн.</th><th>Вартість без ПДВ, грн.</th>'
    for obj in objects:
        message += '<tr>\
                                   <td align="center">{}</td><td>{}</td>\
                                   </tr>' \
            .format(obj['object_code'], obj['object_address'])
    message += '</table><br>'

    message += '<table border="1">\
                               <th>№ п/п</th><th>Назва об’єкту та вид робіт</th><th>Кількість</th>\
                               <th>Ціна, з ПДВ  грн.</th><th>Вартість, з ПДВ грн.</th>'

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
            message += '<tr align="center">\
                                   <td>{}</td><td align="left">{} {}</td><td>{}</td><td>{}</td><td>{}</td>\
                                   </tr>' \
                .format(index, ptype['project_type__description'], object_list,
                        count, ptype['project_type__price'], value)

    woVAT = round(svalue / 6 * 5, 2)
    VAT = round(svalue / 6, 2)
    message += '<tr align="center"><td colspan="2" rowspan="3">Загальна вартість</td>\
                               <td colspan="3">без ПДВ: {} грн. {} коп.</td></tr>\
                               <tr align="center"><td colspan="3">ПДВ: {} грн. {} коп.</td></tr>\
                               <tr align="center"><td colspan="3">з ПДВ: {} грн. {} коп.</td></tr>' \
        .format(int(woVAT), int((woVAT - int(woVAT)) * 100),
                int(VAT), int((VAT - int(VAT)) * 100),
                int(svalue), int((svalue - int(svalue)) * 100))

    message += '</table>'

    return message
