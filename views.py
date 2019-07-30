# -*- coding: utf-8 -*-
from .models import IntTask
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .forms import *
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, date
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from planner.eventlog.models import Log
from django.db.models import Q
from django.db import transaction
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import PermissionDenied
from . import calc_scripts
from crum import get_current_user


@login_required()
def calculation(request, deal_id):
    if not request.user.groups.filter(name='Бухгалтери').exists():
        raise PermissionDenied

    deal = Deal.objects.get(id=deal_id)
    tasks = Task.objects.filter(deal=deal)

    template = getattr(calc_scripts, deal.customer.act_template)

    if tasks.exists():
        report = template(deal, tasks)
    else:
        report = 'Відсутні проекти'

    return HttpResponse(report)


@login_required()
def bonus_calc(request, employee_id, year, month):

    employee = Employee.objects.get(id=employee_id)

    if not request.user.is_superuser and request.user != employee.user and request.user != employee.head.user:
        raise PermissionDenied

    report = calc_scripts.bonus_calculation(request, employee, year, month)

    return HttpResponse(report)


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


@method_decorator(login_required, name='dispatch')
class DealList(ListView):
    model = Deal
    context_object_name = 'deals'  # Default: object_list
    paginate_by = 50
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super(DealList, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_queryset(self):
        deals = Deal.objects.all()
        search_string = self.request.GET.get('filter', '').split()
        customer = self.request.GET.get('customer', '0')
        company = self.request.GET.get('company', '0')
        act_status = self.request.GET.get('act_status', '0')
        pay_status = self.request.GET.get('pay_status', '0')
        order = self.request.GET.get('o', '0')
        for word in search_string:
            deals = deals.filter(Q(number__icontains=word) |
                                 Q(value__icontains=word))
        if customer != '0':
            deals = deals.filter(customer=customer)
        if company != '0':
            deals = deals.filter(company=company)
        if act_status != '0':
            deals = deals.filter(act_status=act_status)
        if pay_status != '0':
            deals = deals.filter(pay_status=pay_status)
        if order != '0':
            deals = deals.order_by(order)
        return deals

    def get_context_data(self, **kwargs):
        context = super(DealList, self).get_context_data(**kwargs)
        context['deals_count'] = Deal.objects.all().count()
        context['deals_filtered'] = self.get_queryset().count()
        self.request.session['deal_query_string'] = self.request.META['QUERY_STRING']
        if self.request.POST:
            context['filter_form'] = DealFilterForm(self.request.POST)
        else:
            context['filter_form'] = DealFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class DealUpdate(UpdateView):
    model = Deal
    form_class = DealForm
    context_object_name = 'deal'

    def get_success_url(self):
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(DealUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = TasksFormSet(self.request.POST, instance=self.object)
        else:
            context['tasks_formset'] = TasksFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        tasks_formset = context['tasks_formset']
        if tasks_formset.is_valid():
            with transaction.atomic():
                form.save()
                tasks_formset.instance = self.object
                tasks_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class DealCreate(CreateView):
    model = Deal
    form_class = DealForm
    context_object_name = 'deal'

    def get_success_url(self):
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(DealCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = TasksFormSet(self.request.POST)
        else:
            context['tasks_formset'] = TasksFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        tasks_formset = context['tasks_formset']
        if form.is_valid() and tasks_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                tasks_formset.instance = self.object
                tasks_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class DealDelete(DeleteView):
    model = Deal

    def get_success_url(self):
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(DealDelete, self).get_context_data(**kwargs)
        obj = self.get_object()
        if obj.task_set.exists():
            context['tasks'] = obj.task_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class TaskList(ListView):
    model = Task
    context_object_name = 'tasks'  # Default: object_list
    paginate_by = 50
    success_url = reverse_lazy('home_page')

    def get_queryset(self):
        tasks = Task.objects.all()
        search_string = self.request.GET.get('filter', '').split()
        exec_status = self.request.GET.get('exec_status', '0')
        owner = self.request.GET.get('owner', '0')
        customer = self.request.GET.get('customer', '0')
        order = self.request.GET.get('o', '0')
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
        return tasks

    def get_context_data(self, **kwargs):
        context = super(TaskList, self).get_context_data(**kwargs)
        context['tasks_count'] = Task.objects.all().count()
        context['tasks_filtered'] = self.get_queryset().count()
        self.request.session['task_query_string'] = self.request.META['QUERY_STRING']
        if self.request.POST:
            context['filter_form'] = TaskFilterForm(self.request.POST)
        else:
            context['filter_form'] = TaskFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class TaskDetail(DetailView):
    model = Task
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super(TaskDetail, self).get_context_data(**kwargs)
        context['executors'] = Execution.objects.filter(task=self.kwargs['pk'])
        context['costs'] = Order.objects.filter(task=self.kwargs['pk'])
        context['sendings'] = Sending.objects.filter(task=self.kwargs['pk'])
        return context


@method_decorator(login_required, name='dispatch')
class TaskUpdate(UpdateView):
    model = Task
    form_class = TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(TaskUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = ExecutorsFormSet(self.request.POST, instance=self.object)
            context['costs_formset'] = CostsFormSet(self.request.POST, instance=self.object)
            context['sending_formset'] = SendingFormSet(self.request.POST, instance=self.object)
        else:
            context['executors_formset'] = ExecutorsFormSet(instance=self.object)
            context['costs_formset'] = CostsFormSet(instance=self.object)
            context['sending_formset'] = SendingFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        executors_formset = context['executors_formset']
        costs_formset = context['costs_formset']
        sending_formset = context['sending_formset']
        if form.is_valid() and executors_formset.is_valid()\
                and costs_formset.is_valid() and sending_formset.is_valid():
            with transaction.atomic():
                form.save()
                executors_formset.instance = self.object
                executors_formset.save()
                costs_formset.instance = self.object
                costs_formset.save()
                sending_formset.instance = self.object
                sending_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class TaskCreate(CreateView):
    model = Task
    form_class = TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(TaskCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = ExecutorsFormSet(self.request.POST)
            context['costs_formset'] = CostsFormSet(self.request.POST)
            context['sending_formset'] = SendingFormSet(self.request.POST)
        else:
            context['executors_formset'] = ExecutorsFormSet()
            context['costs_formset'] = CostsFormSet()
            context['sending_formset'] = SendingFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        executors_formset = context['executors_formset']
        costs_formset = context['costs_formset']
        sending_formset = context['sending_formset']
        if form.is_valid() and executors_formset.is_valid()\
                and costs_formset.is_valid() and sending_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                executors_formset.instance = self.object
                executors_formset.save()
                costs_formset.instance = self.object
                costs_formset.save()
                sending_formset.instance = self.object
                sending_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class TaskDelete(DeleteView):
    model = Task

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string')
        return self.success_url


@method_decorator(login_required, name='dispatch')
class TaskExchange(FormView):
    template_name = 'planner/task_exchange.html'
    form_class = TaskExchangeForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string')
        return self.success_url

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            self.tasks_ids = self.request.GET.getlist('ids', '')
            return super(TaskExchange, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super(TaskExchange, self).get_form_kwargs()
        kwargs['tasks_ids'] = self.tasks_ids
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(TaskExchange, self).get_context_data(**kwargs)
        tasks = Task.objects.filter(id__in=self.tasks_ids)
        context["tasks_ids"] = self.tasks_ids
        context["tasks"] = tasks
        context["query_string"] = self.request.session.get('task_query_string')
        return context

    def form_valid(self, form):
        deal_id = form.cleaned_data['deal']
        if deal_id:
            deal_new = Deal.objects.get(pk=deal_id)
            tasks = Task.objects.filter(id__in=self.tasks_ids)
            deals_old = set()
            for task in tasks:
                deal_old = Deal.objects.get(id=task.deal.pk)
                task.deal = deal_new
                task.save()
                deals_old.add(deal_old)
            for deal in deals_old:
                deal.value = deal.value_calc()
                deal.save()
            deal_new.value = deal_new.value_calc()
            deal_new.save()
        return super(TaskExchange, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
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


@method_decorator(login_required, name='dispatch')
class InttaskDetail(DetailView):
    model = IntTask
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class NewsList(ListView):
    model = News
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class NewsDetail(DetailView):
    model = News
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsCreate(CreateView):
    model = News
    form_class = NewsForm
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsUpdate(UpdateView):
    model = News
    form_class = NewsForm
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsDelete(DeleteView):
    model = News
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class EventList(ListView):
    model = Event
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class EventDetail(DetailView):
    model = Event


@method_decorator(login_required, name='dispatch')
class EventCreate(CreateView):
    model = Event
    form_class = EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventUpdate(UpdateView):
    model = Event
    form_class = EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventDelete(DeleteView):
    model = Event
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EmployeeUpdate(UpdateView):
    model = Employee
    form_class = EmployeeForm
    success_url = reverse_lazy('home_page')

    def get_object(self):
        return Employee.objects.get(user=get_current_user())
