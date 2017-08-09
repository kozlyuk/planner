from .models import Deal, Task, Execution, IntTask, Employee, News, Event
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserLoginForm, TaskFilterForm
from .utils import get_pagination
from django.shortcuts import render_to_response, redirect, render
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, date
from django.core.urlresolvers import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView


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
    if not request.user.is_superuser and request.user != employee.user and\
            (not employee.head.user or request.user != employee.head.user):
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


def login_page(request):
    if request.user.is_authenticated():
        return redirect('home_page')
    if request.method == 'POST':
        login_form = UserLoginForm(request.POST)
        if login_form.is_valid():
            user = authenticate(username=login_form.cleaned_data['username'],
                                password=login_form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                # if 'next' in request.REQUEST:
                #     return redirect(request.REQUEST)
                return redirect('home_page')
            else:
                return render(request, 'auth.html', {'form': login_form, 'not_valid_user': True})
        else:
            return render(request, 'auth.html', {'form': login_form, 'not_valid': True})
    else:
        login_form = UserLoginForm()
    return render(request, 'auth.html', {'form': login_form})


@login_required()
def logout_page(request):
    if request.user.is_authenticated():
        logout(request)
    return redirect('login_page')


@login_required()
def home_page(request):

    if request.user.groups.filter(name='Бухгалтери').exists():
        actneed_deals = []
        active_deals = Deal.objects.exclude(act_status=Deal.Issued) \
                            .exclude(number__icontains='загальний')
        for deal in active_deals:
            if deal.exec_status() == 'Виконано':
                actneed_deals.append(deal)
        debtor_deals = []
        unpaid_deals = Deal.objects.exclude(act_status=Deal.NotIssued) \
                                   .exclude(pay_status=Deal.PaidUp) \
                                   .exclude(number__icontains='загальний')
        deb_deals = unpaid_deals.exclude(pay_date__isnull=True) \
                                .exclude(pay_date__gte=date.today())
        for deal in deb_deals:
            if deal.exec_status() == 'Виконано':
                debtor_deals.append(deal)
        overdue_deals = []
        deals = Deal.objects.exclude(expire_date__gte=date.today()) \
                            .exclude(number__icontains='загальний')
        for deal in deals:
            if deal.exec_status() != 'Виконано':
                overdue_deals.append(deal)

        actneed_deals_count = len(actneed_deals)
        active_deals_count = active_deals.count()
        deals_div = int(actneed_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0
        debtor_deals_count = len(debtor_deals)
        unpaid_deals_count = unpaid_deals.count()
        debtor_deals_div = int(debtor_deals_count / unpaid_deals_count * 100) if unpaid_deals_count > 0 else 0
        overdue_deals_count = len(overdue_deals)
        overdue_deals_div = int(overdue_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0
    elif request.user.groups.filter(name='ГІПи').exists():
        td_tasks = Task.objects.filter(owner__user=request.user, exec_status=Task.ToDo).order_by('creation_date')
        ip_tasks = Task.objects.filter(owner__user=request.user, exec_status=Task.InProgress).order_by('creation_date')
        hd_tasks = Task.objects.filter(owner__user=request.user, exec_status=Task.Done).order_by('-actual_finish')[:50]

        hd_tasks_count = Task.objects.filter(owner__user=request.user, exec_status=Task.Done,
                                             actual_finish__month=datetime.now().month,
                                             actual_finish__year=datetime.now().year).count()
        active_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Done).count() + hd_tasks_count
        tasks_div = int(hd_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        overdue_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Done)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__isnull=True)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__gte=date.today())\
                                      .count()
        overdue_tasks_div = int(overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
    else:
        td_tasks = Task.objects.filter(executors__user=request.user, exec_status=Task.ToDo).order_by('creation_date')
        ip_tasks = Task.objects.filter(executors__user=request.user, exec_status=Task.InProgress).order_by('creation_date')
        hd_tasks = Task.objects.filter(executors__user=request.user, exec_status=Task.Done).order_by('-actual_finish')[:50]
        hd_tasks_count = Task.objects.filter(executors__user=request.user, exec_status=Task.Done,
                                             actual_finish__month=datetime.now().month,
                                             actual_finish__year=datetime.now().year).count()
        active_tasks_count = Task.objects.filter(executors__user=request.user).exclude(exec_status=Task.Done).count() + hd_tasks_count
        tasks_div = int(hd_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        overdue_tasks_count = Task.objects.filter(executors__user=request.user).exclude(exec_status=Task.Done)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__isnull=True)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__gte=date.today())\
                                      .count()
        overdue_tasks_div = int(overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0

    td_inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.ToDo).order_by
    ip_inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.InProgress)
    hd_inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.Done).order_by('-actual_finish')[:50]

    hd_inttasks_count = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.Done,
                                               actual_finish__month=datetime.now().month,
                                               actual_finish__year=datetime.now().year).count()
    active_inttasks_count = IntTask.objects.filter(executor__user=request.user)\
                                           .exclude(exec_status=IntTask.Done).count() + hd_inttasks_count
    inttasks_div = int(hd_inttasks_count / active_inttasks_count * 100) if active_inttasks_count > 0 else 0
    overdue_inttasks_count = IntTask.objects.filter(executor__user=request.user)\
                                            .exclude(exec_status=IntTask.Done)\
                                            .exclude(planned_finish__gte=date.today()).count()
    overdue_inttasks_div = int(overdue_inttasks_count / active_inttasks_count * 100) if active_inttasks_count > 0 else 0

    def date_delta(delta):
        month = datetime.now().month + delta
        year = datetime.now().year
        if month < 1:
            month += 12
            year += -1
        return month, year

    def exec_bonuses(delta):
        bonuses = 0
        month, year = date_delta(delta)
        executions = Execution.objects.filter(executor__user=request.user,
                                              task__exec_status=Task.Done,
                                              task__actual_finish__month=month,
                                              task__actual_finish__year=year, part__gt=0)
        for query in executions:
            bonuses += query.task.exec_bonus(query.part)
        return round(bonuses, 2)
        # executor bonuses

    def owner_bonuses(delta):
        bonuses = 0
        month, year = date_delta(delta)
        tasks = Task.objects.filter(owner__user=request.user,
                                    exec_status=Task.Done,
                                    actual_finish__month=month,
                                    actual_finish__year=year)
        for query in tasks:
            bonuses += query.owner_bonus()

        return round(bonuses, 2)
        # owner bonuses

    def inttask_bonuses(delta):
        bonuses = 0
        month, year = date_delta(delta)
        inttasks = IntTask.objects.filter(executor__user=request.user,
                                          exec_status=IntTask.Done,
                                          actual_finish__month=month,
                                          actual_finish__year=year)
        for query in inttasks:
            bonuses += query.bonus
        return round(bonuses, 2)
        # inttask bonuses

    exec_bonuses_cm = exec_bonuses(0)
    exec_bonuses_pm = exec_bonuses(-1)
    exec_bonuses_ppm = exec_bonuses(-2)
    owner_bonuses_cm = owner_bonuses(0)
    owner_bonuses_pm = owner_bonuses(-1)
    owner_bonuses_ppm = owner_bonuses(-2)
    inttask_bonuses_cm = inttask_bonuses(0)
    inttask_bonuses_pm = inttask_bonuses(-1)
    inttask_bonuses_ppm = inttask_bonuses(-2)
    total_bonuses_cm = exec_bonuses_cm + owner_bonuses_cm + inttask_bonuses_cm
    total_bonuses_pm = exec_bonuses_pm + owner_bonuses_pm + inttask_bonuses_pm
    total_bonuses_ppm = exec_bonuses_ppm + owner_bonuses_ppm + inttask_bonuses_ppm

    news = News.objects.exclude(actual_from__gt=date.today()).exclude(actual_to__lte=date.today()).order_by('-created')

    for event in Event.objects.all():
        event.next_date = event.next_repeat()
        event.save(update_fields=['next_date'])
    events = Event.objects.filter(next_date__isnull=False).order_by('next_date')

    if request.user.groups.filter(name='Бухгалтери').exists():
        return render_to_response('content_admin.html',
                                  {
                                      'employee': request.user.employee,
                                      'actneed_deals': actneed_deals,
                                      'debtor_deals': debtor_deals,
                                      'overdue_deals': overdue_deals,
                                      'td_inttasks': td_inttasks,
                                      'ip_inttasks': ip_inttasks,
                                      'hd_inttasks': hd_inttasks,
                                      'actneed_deals_count': actneed_deals_count,
                                      'active_deals_count': active_deals_count,
                                      'deals_div': deals_div,
                                      'debtor_deals_count': debtor_deals_count,
                                      'unpaid_deals_count': unpaid_deals_count,
                                      'debtor_deals_div': debtor_deals_div,
                                      'overdue_deals_count': overdue_deals_count,
                                      'overdue_deals_div': overdue_deals_div,
                                      'hd_inttasks_count': hd_inttasks_count,
                                      'active_inttasks_count': active_inttasks_count,
                                      'inttasks_div': inttasks_div,
                                      'overdue_inttasks_count': overdue_inttasks_count,
                                      'overdue_inttasks_div': overdue_inttasks_div,
                                      'exec_bonuses_cm': exec_bonuses_cm,
                                      'exec_bonuses_pm': exec_bonuses_pm,
                                      'exec_bonuses_ppm': exec_bonuses_ppm,
                                      'owner_bonuses_cm': owner_bonuses_cm,
                                      'owner_bonuses_pm': owner_bonuses_pm,
                                      'owner_bonuses_ppm': owner_bonuses_ppm,
                                      'inttask_bonuses_cm': inttask_bonuses_cm,
                                      'inttask_bonuses_pm': inttask_bonuses_pm,
                                      'inttask_bonuses_ppm': inttask_bonuses_ppm,
                                      'total_bonuses_cm': total_bonuses_cm,
                                      'total_bonuses_pm': total_bonuses_pm,
                                      'total_bonuses_ppm': total_bonuses_ppm,
                                      'employee_id': Employee.objects.get(user=request.user).id,
                                      'cm': date_delta(0),
                                      'pm': date_delta(-1),
                                      'ppm': date_delta(-2),
                                      'news': news,
                                      'events': events
                                  }, context_instance=RequestContext(request))
    else:
        return render_to_response('content_exec.html',
                                  {
                                      'employee': request.user.employee,
                                      'td_tasks': td_tasks,
                                      'ip_tasks': ip_tasks,
                                      'hd_tasks': hd_tasks,
                                      'td_inttasks': td_inttasks,
                                      'ip_inttasks': ip_inttasks,
                                      'hd_inttasks': hd_inttasks,
                                      'hd_tasks_count': hd_tasks_count,
                                      'active_tasks_count': active_tasks_count,
                                      'tasks_div': tasks_div,
                                      'overdue_tasks_count': overdue_tasks_count,
                                      'overdue_tasks_div': overdue_tasks_div,
                                      'hd_inttasks_count': hd_inttasks_count,
                                      'active_inttasks_count': active_inttasks_count,
                                      'inttasks_div': inttasks_div,
                                      'overdue_inttasks_count': overdue_inttasks_count,
                                      'overdue_inttasks_div': overdue_inttasks_div,
                                      'exec_bonuses_cm': exec_bonuses_cm,
                                      'exec_bonuses_pm': exec_bonuses_pm,
                                      'exec_bonuses_ppm': exec_bonuses_ppm,
                                      'owner_bonuses_cm': owner_bonuses_cm,
                                      'owner_bonuses_pm': owner_bonuses_pm,
                                      'owner_bonuses_ppm': owner_bonuses_ppm,
                                      'inttask_bonuses_cm': inttask_bonuses_cm,
                                      'inttask_bonuses_pm': inttask_bonuses_pm,
                                      'inttask_bonuses_ppm': inttask_bonuses_ppm,
                                      'total_bonuses_cm': total_bonuses_cm,
                                      'total_bonuses_pm': total_bonuses_pm,
                                      'total_bonuses_ppm': total_bonuses_ppm,
                                      'employee_id': Employee.objects.get(user=request.user).id,
                                      'cm': date_delta(0),
                                      'pm': date_delta(-1),
                                      'ppm': date_delta(-2),
                                      'news': news,
                                      'events': events
                                  }, context_instance=RequestContext(request))


@login_required()
def projects_list(request):
    filter_form = TaskFilterForm(request.user, request.GET)
    filter_form.is_valid()

    if request.user.is_superuser:
        tasks = Task.objects.all().order_by('-planned_finish')
    else:
        tasks = Task.get_accessable(request.user).order_by('-planned_finish')

    # if 'field_type' in request.GET:
    #     if request.GET['field_type'] == 'D1':
    #         name = _('Demo first category')
    #     if request.GET['field_type'] == 'D2':
    #         name = _('Demo second category')
    #     if request.GET['field_type'] == 'FC':
    #         name = _('Field checkup report')
    #     if request.GET['field_type'] != u'' and request.GET['field_type'] != u'0':
    #         fields = fields.filter(field_type=request.GET['field_type'])
    # else:
    #     name = ''
    # fields = fields \
    #     .annotate(last_edit=Max('fieldreport__report_date')) \
    #     .order_by('-last_edit', '-last_edit_date')

    page_objects, indexes = get_pagination(tasks, request.GET.get('page', 1), 10)

    return render_to_response('project_list.html',
                              {
                                  'filter_form': filter_form,
                                  'page_objects': page_objects,
                                  'indexes': indexes,
                              },
                              context_instance=RequestContext(request))


@login_required()
def project_details(request, project_id):
    task = Task.objects.get(pk=project_id)
    executors = Execution.objects.filter(task=task)
    return render_to_response('project_view.html',
                              {
                                  'task': task,
                                  'executors': executors,
                              },
                              context_instance=RequestContext(request))


class NewsList(ListView):
    model = News
    success_url = reverse_lazy('home_page')


class NewsDetail(DetailView):
    model = News
    success_url = reverse_lazy('news_list')


class NewsCreate(CreateView):
    model = News
    fields = ['title', 'text', 'news_type', 'actual_from', 'actual_to']
    success_url = reverse_lazy('news_list')

    def get_form(self, form_class):
        form = super(NewsCreate, self).get_form(form_class)
        form.fields['actual_from'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        form.fields['actual_to'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        return form


class NewsUpdate(UpdateView):
    model = News
    fields = ['title', 'text', 'news_type', 'actual_from', 'actual_to']
    template_name_suffix = '_update'
    success_url = reverse_lazy('news_list')

    def get_form(self, form_class):
        form = super(NewsUpdate, self).get_form(form_class)
        form.fields['actual_from'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        form.fields['actual_to'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        return form


class NewsDelete(DeleteView):
    model = News
    success_url = reverse_lazy('news_list')


class EventList(ListView):
    model = Event
    success_url = reverse_lazy('home_page')


class EventDetail(DetailView):
    model = Event
    success_url = reverse_lazy('event_list')


class EventCreate(CreateView):
    model = Event
    fields = ['title', 'date', 'repeat', 'description']
    success_url = reverse_lazy('event_list')

    def get_form(self, form_class):
        form = super(EventCreate, self).get_form(form_class)
        form.fields['date'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        return form


class EventUpdate(UpdateView):
    model = Event
    fields = ['title', 'date', 'repeat', 'description']
    template_name_suffix = '_update'
    success_url = reverse_lazy('event_list')

    def get_form(self, form_class):
        form = super(EventUpdate, self).get_form(form_class)
        form.fields['date'].widget.attrs.update({'class': 'date-picker', 'data-date-format': 'dd.mm.yyyy'})
        return form


class EventDelete(DeleteView):
    model = Event
    success_url = reverse_lazy('event_list')

#@login_required()
#def project_form(request, project_id=0):
#    pass


#@login_required()
#def deals_list(request):
#    pass