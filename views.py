# -*- coding: utf-8 -*-
from .models import Deal, Task, Execution, IntTask, Employee, News, Event, Order, Sending
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserLoginForm, TaskFilterForm
from .forms import TaskForm, ExecutorsFormSet, CostsFormSet, SendingFormSet
from .utils import get_pagination
from django.shortcuts import redirect, render, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, date
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django import forms
from eventlog.models import Log
from django.db.models import Q
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import PermissionDenied


@login_required()
def calculation(request, deal_id):
    if not request.user.groups.filter(name='Бухгалтери').exists():
        raise PermissionDenied

    deal = Deal.objects.get(id=deal_id)
    tasks = Task.objects.filter(deal=deal)

    if tasks.exists():

        message = '<html><body>Калькуляція по договору {} від {}:<br><br>'\
                  .format(deal, deal.date.strftime('%d.%m.%Y'))

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
        raise PermissionDenied

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
    if request.user.is_authenticated:
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
    if request.user.is_authenticated:
        logout(request)
    return redirect('login_page')


@login_required()
def home_page(request):

    if request.user.groups.filter(name='Бухгалтери').exists():
        actneed_deals = []
        active_deals = Deal.objects.exclude(act_status=Deal.Issued) \
                           .exclude(number__icontains='загальний')
        for deal in active_deals:
            if deal.exec_status() == 'Надіслано':
                actneed_deals.append(deal)
        debtor_deals = []
        unpaid_deals = Deal.objects.exclude(act_status=Deal.NotIssued) \
                                   .exclude(pay_status=Deal.PaidUp) \
                                   .exclude(number__icontains='загальний')
        deb_deals = unpaid_deals.exclude(pay_date__isnull=True) \
                                .exclude(pay_date__gte=date.today())
        for deal in deb_deals:
            if deal.exec_status() == 'Надіслано':
                debtor_deals.append(deal)
        overdue_deals = []
        deals = Deal.objects.exclude(expire_date__gte=date.today()) \
                            .exclude(number__icontains='загальний')
        for deal in deals:
            if deal.exec_status() != 'Надіслано':
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
        td_tasks = Task.objects.filter(exec_status=Task.ToDo, owner__user=request.user).order_by('creation_date')
        ip_tasks = Task.objects.filter(Q(exec_status=Task.Done) | Q(exec_status=Task.InProgress),
                                       owner__user=request.user).order_by('creation_date')
        hd_tasks = Task.objects.filter(exec_status=Task.Sent, owner__user=request.user).order_by('-actual_finish')[:50]

        hd_tasks_count = Task.objects.filter(owner__user=request.user, exec_status=Task.Sent,
                                             actual_finish__month=datetime.now().month,
                                             actual_finish__year=datetime.now().year).count()
        active_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Sent).count() + hd_tasks_count
        tasks_div = int(hd_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        overdue_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Sent)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__isnull=True)\
                                      .exclude(deal__expire_date__gte=date.today(), planned_finish__gte=date.today())\
                                      .count()
        overdue_tasks_div = int(overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
    else:
        td_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.ToDo).order_by('creation_date')
        ip_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.InProgress).order_by('creation_date')
        hd_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.Done).order_by('-finish_date')[:50]
        hd_executions_count = Execution.objects.filter(executor__user=request.user, exec_status=Execution.Done,
                                                       finish_date__month=datetime.now().month,
                                                       finish_date__year=datetime.now().year).count()
        active_executions_count = Execution.objects.filter(executor__user=request.user)\
                                                   .exclude(exec_status=Execution.Done)\
                                                   .count() + hd_executions_count
        executions_div = int(hd_executions_count / active_executions_count * 100) if active_executions_count > 0 else 0
        overdue_executions_count = Execution.objects.filter(executor__user=request.user)\
                                            .exclude(exec_status=Execution.Done)\
                                            .exclude(task__deal__expire_date__gte=date.today(), task__planned_finish__isnull=True)\
                                            .exclude(task__deal__expire_date__gte=date.today(), task__planned_finish__gte=date.today())\
                                            .count()
        overdue_executions_div = int(overdue_executions_count / active_executions_count * 100) if active_executions_count > 0 else 0

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
        executions = Execution.objects.filter(Q(task__exec_status=Task.Done) | Q(task__exec_status=Task.Sent),
                                              executor__user=request.user,
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
                                    exec_status=Task.Sent,
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
        event.save(update_fields=['next_date'], logging=False)
    events = Event.objects.filter(next_date__isnull=False).order_by('next_date')

    activities = Log.objects.filter(user=request.user)[:50]

    if request.user.groups.filter(name='Бухгалтери').exists():
        return render(request, 'content_admin.html',
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
                                      'events': events,
                                      'activities': activities
                                  })
    elif request.user.groups.filter(name='ГІПи').exists():
        return render(request, 'content_gip.html',
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
                                      'events': events,
                                      'activities': activities
                                  })
    else:
        return render(request, 'content_exec.html',
                                  {
                                      'employee': request.user.employee,
                                      'td_executions': td_executions,
                                      'ip_executions': ip_executions,
                                      'hd_executions': hd_executions,
                                      'td_inttasks': td_inttasks,
                                      'ip_inttasks': ip_inttasks,
                                      'hd_inttasks': hd_inttasks,
                                      'hd_executions_count': hd_executions_count,
                                      'active_executions_count': active_executions_count,
                                      'executions_div': executions_div,
                                      'overdue_executions_count': overdue_executions_count,
                                      'overdue_executions_div': overdue_executions_div,
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
                                      'events': events,
                                      'activities': activities
                                  })


@login_required()
def projects_list(request):
    filter_form = TaskFilterForm(request.user, request.GET)
    filter_form.is_valid()

    tasks = Task.get_accessable(request.user).order_by('-planned_finish')
    tasks_count = tasks.count()

    search_string = request.GET.get('filter', '').split()
    exec_status = request.GET.get('exec_status', '0')
    owner = request.GET.get('owner', '0')
    customer = request.GET.get('customer', '0')
    order = request.GET.get('o', '0')
    for word in search_string:
        tasks = tasks.filter(Q(object_code__icontains=word) |
                         Q(object_address__icontains=word) |
                         Q(deal__number__icontains=word) |
                         Q(project_type__price_code__icontains=word) |
                         Q(project_type__project_type__icontains=word))
    if exec_status != '0':
        tasks = tasks.filter(exec_status=exec_status)
    if owner != '0':
        tasks = tasks.filter(owner=owner)
    if customer != '0':
        tasks = tasks.filter(deal__customer=customer)
    if order != '0':
        tasks = tasks.order_by(order)
    else:
        tasks = tasks.order_by('-creation_date', '-deal', 'object_code')
    tasks_filtered = tasks.count()

    page_objects, indexes = get_pagination(tasks, request.GET.get('page', 1), 50)

    return render(request, 'project_list.html',
                              {
                                  'filter_form': filter_form,
                                  'page_objects': page_objects,
                                  'indexes': indexes,
                                  'tasks_count': tasks_count,
                                  'tasks_filtered': tasks_filtered,
                                  'filters': request.META['QUERY_STRING']
                              })


@login_required()
def task_detail(request, project_id):
    task = Task.objects.get(pk=project_id)
    executors = Execution.objects.filter(task=task)
    costs = Order.objects.filter(task=task)
    sendings = Sending.objects.filter(task=task)
    return render(request, 'planner/task_detail.html',
                              {
                                  'task': task,
                                  'executors': executors,
                                  'costs': costs,
                                  'sendings': sendings,
                                  'filters': request.META['QUERY_STRING']
                              })


class TaskUpdate(UpdateView):
    model = Task
    form_class = TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('projects_list') + '?' + self.request.META['QUERY_STRING']
        return self.success_url

    def get_form(self, form_class=None):
        form = super(TaskUpdate, self).get_form(form_class)
        form.fields['planned_start'].widget = AdminDateWidget()
        form.fields['planned_finish'].widget = AdminDateWidget()
        form.fields['actual_start'].widget = AdminDateWidget()
        form.fields['actual_finish'].widget = AdminDateWidget()
        form.fields['object_address'].widget.attrs.update({'size': 70})
        form.fields['comment'].widget.attrs.update({'cols': 70, 'rows': 3})
        return form

    def get_context_data(self, **kwargs):
        context = super(TaskUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_form'] = ExecutorsFormSet(self.request.POST, instance=self.object)
            context['costs_form'] = CostsFormSet(self.request.POST, instance=self.object)
            context['sending_form'] = SendingFormSet(self.request.POST, instance=self.object)
        else:
            context['executors_form'] = ExecutorsFormSet(instance=self.object)
            context['costs_form'] = CostsFormSet(instance=self.object)
            context['sending_form'] = SendingFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        executors_form = context['executors_form']
        costs_form = context['costs_form']
        sending_form = context['sending_form']
        if executors_form.is_valid() and costs_form.is_valid() and sending_form.is_valid():
            executors_form.instance = self.object
            executors_form.save()
            costs_form.instance = self.object
            costs_form.save()
            sending_form.instance = self.object
            sending_form.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class TaskCreate(CreateView):
    model = Task
    form_class = TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('projects_list') + '?' + self.request.META['QUERY_STRING']
        return self.success_url

    def get_form(self, form_class=None):
        form = super(TaskCreate, self).get_form(form_class)
        form.fields['planned_start'].widget = AdminDateWidget()
        form.fields['planned_finish'].widget = AdminDateWidget()
        form.fields['actual_start'].widget = AdminDateWidget()
        form.fields['actual_finish'].widget = AdminDateWidget()
        form.fields['object_address'].widget.attrs.update({'size': 70})
        form.fields['comment'].widget.attrs.update({'cols': 70, 'rows': 3})
        return form

    def get_context_data(self, **kwargs):
        context = super(TaskCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_form'] = ExecutorsFormSet(self.request.POST, instance=self.object)
            context['costs_form'] = CostsFormSet(self.request.POST, instance=self.object)
            context['sending_form'] = SendingFormSet(self.request.POST, instance=self.object)
        else:
            context['executors_form'] = ExecutorsFormSet(instance=self.object)
            context['costs_form'] = CostsFormSet(instance=self.object)
            context['sending_form'] = SendingFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        executors_form = context['executors_form']
        costs_form = context['costs_form']
        sending_form = context['sending_form']
        if executors_form.is_valid() and costs_form.is_valid() and sending_form.is_valid():
            self.object = form.save()
            executors_form.instance = self.object
            executors_form.save()
            costs_form.instance = self.object
            costs_form.save()
            sending_form.instance = self.object
            sending_form.save()
        return HttpResponseRedirect(self.get_success_url())


class SubtaskUpdate(UpdateView):
    model = Execution
    fields = ['exec_status', 'finish_date']
    success_url = reverse_lazy('home_page')

    def get_form(self, form_class=None):
        form = super(SubtaskUpdate, self).get_form(form_class)
        form.fields['finish_date'].widget = AdminDateWidget()
        return form

    def get_context_data(self, **kwargs):
        context = super(SubtaskUpdate, self).get_context_data(**kwargs)
        execution = Execution.objects.get(pk=self.kwargs['pk'])
        context['executors'] = Execution.objects.filter(task=execution.task)
        context['sendings'] = Sending.objects.filter(task=execution.task)
        return context

    def form_valid(self, form):
        if form.cleaned_data['finish_date'] and form.cleaned_data['exec_status'] != Execution.Done:
            form.add_error('exec_status', "Будь ласка відмітьте Статус виконання або видаліть Дату виконання")
            return self.form_invalid(form)
        elif form.cleaned_data['exec_status'] == Execution.Done and not form.cleaned_data['finish_date']:
            form.add_error('finish_date', "Вкажіть будь ласка Дату виконання робіт")
            return self.form_invalid(form)
        else:
            return super().form_valid(form)


class InttaskDetail(DetailView):
    model = IntTask
    success_url = reverse_lazy('home_page')


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

    def get_form(self, form_class=None):
        form = super(NewsCreate, self).get_form(form_class)
        form.fields['actual_from'].widget = AdminDateWidget()
        form.fields['actual_to'].widget = AdminDateWidget()
        return form


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'text', 'news_type', 'actual_from', 'actual_to']

    def __init__(self, *args, **kwargs):
        super(NewsForm, self).__init__(*args, **kwargs)
        if not self.instance.is_editable():
            self.fields['text'].widget.attrs['readonly'] = True
        self.fields['actual_from'].widget = AdminDateWidget()
        self.fields['actual_to'].widget = AdminDateWidget()


class NewsUpdate(UpdateView):
    model = News
    form_class = NewsForm
    success_url = reverse_lazy('news_list')


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

    def get_form(self, form_class=None):
        form = super(EventCreate, self).get_form(form_class)
        form.fields['date'].widget = AdminDateWidget()
        return form


class EventUpdate(UpdateView):
    model = Event
    fields = ['title', 'date', 'repeat', 'description']
    success_url = reverse_lazy('event_list')

    def get_form(self, form_class=None):
        form = super(EventUpdate, self).get_form(form_class)
        form.fields['date'].widget = AdminDateWidget()
        return form


class EventDelete(DeleteView):
    model = Event
    success_url = reverse_lazy('event_list')
