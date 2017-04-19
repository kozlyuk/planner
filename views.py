from planner.models import Deal, Task
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

        project_types = tasks.values('project_type__price_code', 'project_type__comment', 'project_type__price')\
                             .order_by('project_type__price_code').distinct()

        index = 0
        svalue = 0
        for ptype in project_types:
            if ptype['project_type__price'] != 0:
                index += 1
                object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code']).values_list('object_code', flat=True)
                object_list = ''
                for obj in object_codes:
                    object_list += obj + ' '
                count = object_codes.count()
                value = ptype['project_type__price'] * count
                svalue += value
                message += '<tr align="center">\
                       <td>{}</td><td align="left">{} {}</td><td>{}</td><td>{}</td><td>{}</td>\
                       </tr>'\
                       .format(index, ptype['project_type__comment'], object_list,
                              count, ptype['project_type__price'], value)

        woVAT = round(svalue/6*5, 2)
        VAT = round(svalue/6, 2)
        message += '<tr align="center"><td colspan="2" rowspan="3">Загальна вартість</td><td colspan="3">без ПДВ: {} грн. 00 коп.</td></tr>\
                   <tr align="center"><td colspan="3">ПДВ: {} грн. 00 коп.</td></tr>\
                   <tr align="center"><td colspan="3">з ПДВ: {} грн. 00 коп.</td></tr>'\
                   .format(woVAT, VAT, svalue)

        message += '</table>'

    subject = "Калькуляція по Договору"

    return HttpResponse(message)
