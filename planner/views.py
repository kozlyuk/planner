# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from planner import forms
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, date
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic import FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from eventlog.models import Log
from django.db.models import Func
from django.db.models import Q, F, Value, ExpressionWrapper, DecimalField, FloatField
from django.db.models.functions import Concat
from django.db import transaction
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import PermissionDenied
from crum import get_current_user
from planner.models import Task, Deal, Employee, Project, Execution, Receiver, Sending, Order, IntTask, News, Event


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 2)'


@method_decorator(login_required, name='dispatch')
class DealCalc(TemplateView):
    """ View for displaying calculation to a deal """
    template_name = "deal_calc.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deal = Deal.objects.get(id=self.kwargs['deal_id'])
        tasks = Task.objects.filter(deal=deal)
        objects = tasks.values('object_code', 'object_address').order_by().distinct()
        template = deal.customer.act_template

        index = 0
        svalue = 0
        object_lists = []
        if template == 'gks':
            project_types = tasks.values('project_type__price_code', 'project_type__description', 'project_type__price') \
                .order_by('project_type__price_code').distinct()
            for ptype in project_types:
                if ptype['project_type__price'] != 0:
                    index += 1
                    object_codes = tasks.filter(project_type__price_code=ptype['project_type__price_code']) \
                        .values_list('object_code', flat=True)
                    object_list = ''
                    for obj in object_codes:
                        object_list += obj + ' '
                    count = object_codes.count()
                    price = ptype['project_type__price'] / 6 * 5
                    value = price * count
                    svalue += round(value, 2)
                object_lists.append([index, ptype['project_type__description'] + ' ' + object_list,
                                    count, round(price, 2), round(value, 2)])
        elif template == 'msz':
            object_lists = [[] for _ in range(len(objects))]
            for obj in range(len(objects)):
                index += 1
                object_lists[obj].append([objects[obj]['object_code'] + ' ' + objects[obj]['object_address']])
                for task in tasks.filter(object_code=objects[obj]['object_code'])\
                        .values('project_type__price_code', 'project_type__description', 'project_type__price'):
                    if task['project_type__price'] != 0:
                        price = round(task['project_type__price'] / 6 * 5, 2)
                        svalue += price
                    object_lists[obj].append([index, task['project_type__description'], 'шт.', 1, price, price])

        context['deal'] = deal
        context['objects'] = objects
        context['taxation'] = deal.company.taxation
        context['template'] = template
        context['object_lists'] = object_lists
        context['svalue'] = round(svalue, 2)
        return context


@method_decorator(login_required, name='dispatch')
class BonusesCalc(TemplateView):
    """ View for displaying bonuses calculation to a employee """
    template_name = "bonuses_list.html"

    def dispatch(self, request, *args, **kwargs):
        employee = Employee.objects.get(id=self.kwargs['employee_id'])
        if request.user.is_superuser or request.user == employee.user or request.user == employee.head.user:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = Employee.objects.get(id=self.kwargs['employee_id'])

        tasks = Task.objects.filter(owner=employee,
                                    exec_status=Task.Sent,
                                    actual_finish__month=self.kwargs['month'],
                                    actual_finish__year=self.kwargs['year'])
        bonuses = 0
        index = 0
        task_list = []
        for task in tasks:
            index += 1
            task_list.append([index, task.object_code, task.object_address,
                              task.project_type, task.owner_part(),
                              round(task.owner_bonus(), 2)])
            bonuses += task.owner_bonus()

        executions = Execution.objects.filter(Q(task__exec_status=Task.Done) | Q(task__exec_status=Task.Sent),
                                              executor=employee,
                                              task__actual_finish__month=self.kwargs['month'],
                                              task__actual_finish__year=self.kwargs['year'])

        index = 0
        executions_list = []
        for ex in executions:
            index += 1
            executions_list.append([index, ex.task.object_code, ex.task.object_address,
                                   ex.task.project_type, ex.part_name, ex.part,
                                   round(ex.task.exec_bonus(ex.part), 2)])
            bonuses += ex.task.exec_bonus(ex.part)

        inttasks = IntTask.objects.filter(executor=employee,
                                          exec_status=IntTask.Done,
                                          actual_finish__month=self.kwargs['month'],
                                          actual_finish__year=self.kwargs['year'])
        index = 0
        inttasks_list = []
        for task in inttasks:
            index += 1
            inttasks_list.append([index, task.task_name, task.bonus])
            bonuses += task.bonus
        first_name = employee.user.first_name

        bonuses = round( bonuses, 2 )

        context['first_name'] = first_name
        context['tasks'] = task_list
        context['executions'] = executions_list
        context['inttasks'] = inttasks_list
        context['bonuses'] = bonuses
        return context


def login_page(request):
    if request.user.is_authenticated:
        return redirect('home_page')
    if request.method == 'POST':
        login_form = forms.UserLoginForm(request.POST)
        if login_form.is_valid():
            user = authenticate(username=login_form.cleaned_data['username'],
                                password=login_form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                return redirect('home_page')
            return render(request, 'auth.html', {'form': login_form, 'not_valid_user': True})
        return render(request, 'auth.html', {'form': login_form, 'not_valid': True})
    login_form = forms.UserLoginForm()
    return render(request, 'auth.html', {'form': login_form})


@login_required()
def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('login_page')


@login_required()
def home_page(request):

    if request.user.groups.filter(name='Бухгалтери').exists():
        active_deals = Deal.objects.exclude(act_status=Deal.Issued) \
                                   .exclude(number__icontains='загальний')
        actneed_deals = active_deals.filter(exec_status=Deal.Sent)
        unpaid_deals = Deal.objects.exclude(act_status=Deal.NotIssued) \
                                   .exclude(pay_status=Deal.PaidUp) \
                                   .exclude(number__icontains='загальний')
        debtor_deals = unpaid_deals.filter(exec_status=Deal.Sent)\
                                   .exclude(pay_date__isnull=True) \
                                   .exclude(pay_date__gte=date.today())
        overdue_deals = Deal.objects.exclude(exec_status=Deal.Sent) \
                                    .exclude(expire_date__gte=date.today()) \
                                    .exclude(number__icontains='загальний')

        active_deals_count = active_deals.count()
        actneed_deals_count = actneed_deals.count()
        debtor_deals_count = debtor_deals.count()
        unpaid_deals_count = unpaid_deals.count()
        deals_div = int(actneed_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0
        debtor_deals_div = int(debtor_deals_count / unpaid_deals_count * 100) if unpaid_deals_count > 0 else 0
        overdue_deals_count = len(overdue_deals)
        overdue_deals_div = int(overdue_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0
    elif request.user.groups.filter(name='ГІПи').exists():
        td_tasks = Task.objects.filter(exec_status=Task.ToDo, owner__user=request.user).order_by('creation_date')
        ip_tasks = Task.objects.filter(exec_status=Task.InProgress, owner__user=request.user).order_by('creation_date')
        hd_tasks = Task.objects.filter(exec_status=Task.Done, owner__user=request.user).order_by('creation_date')
        sent_tasks = Task.objects.filter(owner__user=request.user, exec_status=Task.Sent,
                                         actual_finish__month=datetime.now().month,
                                         actual_finish__year=datetime.now().year)\
                                 .order_by('-actual_finish')
        td_tasks_count = td_tasks.count()
        ip_tasks_count = ip_tasks.count()
        hd_tasks_count = hd_tasks.count()
        sent_tasks_count = sent_tasks.count()
        active_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Sent).count() + sent_tasks_count
        tasks_div = int(sent_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        overdue_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Sent)\
                                          .exclude(deal__expire_date__gte=date.today(), planned_finish__isnull=True)\
                                          .exclude(deal__expire_date__gte=date.today(), planned_finish__gte=date.today())\
                                          .count()
        overdue_tasks_div = int(overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        owner_productivity = request.user.employee.owner_productivity()
    else:
        td_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.ToDo).order_by('creation_date')
        ip_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.InProgress).order_by('creation_date')
        hd_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.Done,
                               finish_date__month=datetime.now().month, finish_date__year=datetime.now().year)
        td_executions_count = td_executions.count()
        ip_executions_count = ip_executions.count()
        hd_executions_count = hd_executions.count()
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
        productivity = request.user.employee.productivity()

    inttasks = IntTask.objects.filter(executor__user=request.user)\
                              .exclude(exec_status=IntTask.Done)\
                              .order_by('exec_status')
#    inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.To_Do)
#    ip_inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.InProgress)
#    hd_inttasks = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.Done).order_by('-actual_finish')[:50]

    hd_inttasks_count = IntTask.objects.filter(executor__user=request.user, exec_status=IntTask.Done,
                                               actual_finish__month=datetime.now().month,
                                               actual_finish__year=datetime.now().year).count()
    active_inttasks_count = IntTask.objects.filter(executor__user=request.user)\
                                           .exclude(exec_status=IntTask.Done).count() + hd_inttasks_count
#    inttasks_div = int(hd_inttasks_count / active_inttasks_count * 100) if active_inttasks_count > 0 else 0
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
#    exec_bonuses_pm = exec_bonuses(-1)
#    exec_bonuses_ppm = exec_bonuses(-2)
    owner_bonuses_cm = owner_bonuses(0)
#    owner_bonuses_pm = owner_bonuses(-1)
#    owner_bonuses_ppm = owner_bonuses(-2)
    inttask_bonuses_cm = inttask_bonuses(0)
#    inttask_bonuses_pm = inttask_bonuses(-1)
#    inttask_bonuses_ppm = inttask_bonuses(-2)
    total_bonuses_cm = exec_bonuses_cm + owner_bonuses_cm + inttask_bonuses_cm
#    total_bonuses_pm = exec_bonuses_pm + owner_bonuses_pm + inttask_bonuses_pm
#    total_bonuses_ppm = exec_bonuses_ppm + owner_bonuses_ppm + inttask_bonuses_ppm

    news = News.objects.exclude(actual_from__gt=date.today()).exclude(actual_to__lte=date.today()).order_by('-created')
    events = Event.objects.filter(next_date__isnull=False).order_by('next_date')
    activities = Log.objects.filter(user=request.user)[:50]

    if request.user.groups.filter(name='Бухгалтери').exists():
        return render(request, 'content_admin.html',
                                  {
                                      'employee': request.user.employee,
                                      'actneed_deals': actneed_deals,
                                      'debtor_deals': debtor_deals,
                                      'overdue_deals': overdue_deals,
                                      'inttasks': inttasks,
                                      #'td_inttasks': td_inttasks,
                                      #'ip_inttasks': ip_inttasks,
                                      #'hd_inttasks': hd_inttasks,
                                      'actneed_deals_count': actneed_deals_count,
                                      'active_deals_count': active_deals_count,
                                      'deals_div': deals_div,
                                      'debtor_deals_count': debtor_deals_count,
                                      'unpaid_deals_count': unpaid_deals_count,
                                      'debtor_deals_div': debtor_deals_div,
                                      'overdue_deals_count': overdue_deals_count,
                                      'overdue_deals_div': overdue_deals_div,
                                      #'hd_inttasks_count': hd_inttasks_count,
                                      'active_inttasks_count': active_inttasks_count,
                                      #'inttasks_div': inttasks_div,
                                      'overdue_inttasks_count': overdue_inttasks_count,
                                      'overdue_inttasks_div': overdue_inttasks_div,
                                      'exec_bonuses_cm': exec_bonuses_cm,
                                      #'exec_bonuses_pm': exec_bonuses_pm,
                                      #'exec_bonuses_ppm': exec_bonuses_ppm,
                                      'owner_bonuses_cm': owner_bonuses_cm,
                                      #'owner_bonuses_pm': owner_bonuses_pm,
                                      #'owner_bonuses_ppm': owner_bonuses_ppm,
                                      'inttask_bonuses_cm': inttask_bonuses_cm,
                                      #'inttask_bonuses_pm': inttask_bonuses_pm,
                                      #'inttask_bonuses_ppm': inttask_bonuses_ppm,
                                      'total_bonuses_cm': total_bonuses_cm,
                                      #'total_bonuses_pm': total_bonuses_pm,
                                      #'total_bonuses_ppm': total_bonuses_ppm,
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
                                      'sent_tasks': sent_tasks,
                                      'inttasks': inttasks,
                                      #'td_inttasks': td_inttasks,
                                      #'ip_inttasks': ip_inttasks,
                                      #'hd_inttasks': hd_inttasks,
                                      'td_tasks_count': td_tasks_count,
                                      'ip_tasks_count': ip_tasks_count,
                                      'hd_tasks_count': hd_tasks_count,
                                      'sent_tasks_count': sent_tasks_count,
                                      'active_tasks_count': active_tasks_count,
                                      'tasks_div': tasks_div,
                                      'overdue_tasks_count': overdue_tasks_count,
                                      'overdue_tasks_div': overdue_tasks_div,
                                      'owner_productivity': owner_productivity,
                                      #'hd_inttasks_count': hd_inttasks_count,
                                      'active_inttasks_count': active_inttasks_count,
                                      #'inttasks_div': inttasks_div,
                                      'overdue_inttasks_count': overdue_inttasks_count,
                                      'overdue_inttasks_div': overdue_inttasks_div,
                                      'exec_bonuses_cm': exec_bonuses_cm,
                                      #'exec_bonuses_pm': exec_bonuses_pm,
                                      #'exec_bonuses_ppm': exec_bonuses_ppm,
                                      'owner_bonuses_cm': owner_bonuses_cm,
                                      #'owner_bonuses_pm': owner_bonuses_pm,
                                      #'owner_bonuses_ppm': owner_bonuses_ppm,
                                      'inttask_bonuses_cm': inttask_bonuses_cm,
                                      #'inttask_bonuses_pm': inttask_bonuses_pm,
                                      #'inttask_bonuses_ppm': inttask_bonuses_ppm,
                                      'total_bonuses_cm': total_bonuses_cm,
                                      #'total_bonuses_pm': total_bonuses_pm,
                                      #'total_bonuses_ppm': total_bonuses_ppm,
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
                                      'inttasks': inttasks,
                                      #'td_inttasks': td_inttasks,
                                      #'ip_inttasks': ip_inttasks,
                                      #'hd_inttasks': hd_inttasks,
                                      'td_executions_count': td_executions_count,
                                      'ip_executions_count': ip_executions_count,
                                      'hd_executions_count': hd_executions_count,
                                      'active_executions_count': active_executions_count,
                                      'executions_div': executions_div,
                                      'overdue_executions_count': overdue_executions_count,
                                      'overdue_executions_div': overdue_executions_div,
                                      'productivity': productivity,
                                      #'hd_inttasks_count': hd_inttasks_count,
                                      'active_inttasks_count': active_inttasks_count,
                                      #'inttasks_div': inttasks_div,
                                      'overdue_inttasks_count': overdue_inttasks_count,
                                      'overdue_inttasks_div': overdue_inttasks_div,
                                      'exec_bonuses_cm': exec_bonuses_cm,
                                      #'exec_bonuses_pm': exec_bonuses_pm,
                                      #'exec_bonuses_ppm': exec_bonuses_ppm,
                                      'owner_bonuses_cm': owner_bonuses_cm,
                                      #'owner_bonuses_pm': owner_bonuses_pm,
                                      #'owner_bonuses_ppm': owner_bonuses_ppm,
                                      'inttask_bonuses_cm': inttask_bonuses_cm,
                                      #'inttask_bonuses_pm': inttask_bonuses_pm,
                                      #'inttask_bonuses_ppm': inttask_bonuses_ppm,
                                      'total_bonuses_cm': total_bonuses_cm,
                                      #'total_bonuses_pm': total_bonuses_pm,
                                      #'total_bonuses_ppm': total_bonuses_ppm,
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
            context['filter_form'] = forms.DealFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.DealFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class DealUpdate(UpdateView):
    model = Deal
    form_class = forms.DealForm
    context_object_name = 'deal'

    def get_success_url(self):
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string', '')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(DealUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = forms.TasksFormSet(self.request.POST, instance=self.object)
        else:
            context['tasks_formset'] = forms.TasksFormSet(instance=self.object)
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
    form_class = forms.DealForm
    context_object_name = 'deal'

    def get_success_url(self):
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string', '')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(DealCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = forms.TasksFormSet(self.request.POST)
        else:
            context['tasks_formset'] = forms.TasksFormSet()
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
        self.success_url = reverse_lazy('deal_list') + '?' + self.request.session.get('deal_query_string', '')
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
            context['filter_form'] = forms.TaskFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.TaskFilterForm(self.request.GET)
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
    form_class = forms.TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(TaskUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = forms.ExecutorsFormSet(self.request.POST, instance=self.object)
            context['costs_formset'] = forms.CostsFormSet(self.request.POST, instance=self.object)
            context['sending_formset'] = forms.SendingFormSet(self.request.POST, instance=self.object)
        else:
            context['executors_formset'] = forms.ExecutorsFormSet(instance=self.object)
            context['costs_formset'] = forms.CostsFormSet(instance=self.object)
            context['sending_formset'] = forms.SendingFormSet(instance=self.object)
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
    form_class = forms.TaskForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super(TaskCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = forms.ExecutorsFormSet(self.request.POST)
            context['costs_formset'] = forms.CostsFormSet(self.request.POST)
            context['sending_formset'] = forms.SendingFormSet(self.request.POST)
        else:
            context['executors_formset'] = forms.ExecutorsFormSet()
            context['costs_formset'] = forms.CostsFormSet()
            context['sending_formset'] = forms.SendingFormSet()
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
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
        return self.success_url


@method_decorator(login_required, name='dispatch')
class TaskExchange(FormView):
    template_name = 'planner/task_exchange.html'
    form_class = forms.TaskExchangeForm

    def get_success_url(self):
        self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
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
        context["query_string"] = self.request.session.get('task_query_string', '')
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


# @method_decorator(login_required, name='dispatch')
# class TaskRegistry(FormView):
#     template_name = 'planner/task_registry.html'
#     form_class = TaskRegistryForm
#
#     def get_success_url(self):
#         self.success_url = reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
#         return self.success_url
#
#     def dispatch(self, request, *args, **kwargs):
#         if request.user.is_superuser or request.user.groups.filter(name='Секретарі').exists():
#             self.tasks_ids = self.request.GET.getlist('ids', '')
#             return super(TaskExchange, self).dispatch(request, *args, **kwargs)
#         else:
#             raise PermissionDenied
#
#     def get_form_kwargs(self):
#         kwargs = super(TaskExchange, self).get_form_kwargs()
#         kwargs['tasks_ids'] = self.tasks_ids
#         return kwargs
#
#     def get_context_data(self, **kwargs):
#         context = super(TaskExchange, self).get_context_data(**kwargs)
#         tasks = Task.objects.filter(id__in=self.tasks_ids)
#         context["tasks_ids"] = self.tasks_ids
#         context["tasks"] = tasks
#         context["query_string"] = self.request.session.get('task_query_string', '')
#         return context
#
#     def form_valid(self, form):
#         deal_id = form.cleaned_data['deal']
#         if deal_id:
#             deal_new = Deal.objects.get(pk=deal_id)
#             tasks = Task.objects.filter(id__in=self.tasks_ids)
#             deals_old = set()
#             for task in tasks:
#                 deal_old = Deal.objects.get(id=task.deal.pk)
#                 task.deal = deal_new
#                 task.save()
#                 deals_old.add(deal_old)
#             for deal in deals_old:
#                 deal.value = deal.value_calc()
#                 deal.save()
#             deal_new.value = deal_new.value_calc()
#             deal_new.save()
#         return super(TaskExchange, self).form_valid(form)


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
    form_class = forms.NewsForm
    success_url = reverse_lazy('news_list')


@method_decorator(login_required, name='dispatch')
class NewsUpdate(UpdateView):
    model = News
    form_class = forms.NewsForm
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
    form_class = forms.EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventUpdate(UpdateView):
    model = Event
    form_class = forms.EventForm
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EventDelete(DeleteView):
    model = Event
    success_url = reverse_lazy('event_list')


@method_decorator(login_required, name='dispatch')
class EmployeeUpdate(UpdateView):
    model = Employee
    form_class = forms.EmployeeForm
    success_url = reverse_lazy('home_page')

    def get_object(self):
        return Employee.objects.get(user=get_current_user())


@method_decorator(login_required, name='dispatch')
class ReceiverList(ListView):
    """ ListView for Receivers.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Receiver
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15
    
    def get_queryset(self):  # todo args url
        receivers = Receiver.objects.annotate(url=Concat(F('pk'), Value('/change/'))).\
            values_list('name', 'address', 'contact_person', 'phone', 'url')
        search_string = self.request.GET.get('filter', '').split()
        order = self.request.GET.get('o', '0')
        for word in search_string:
            receivers = receivers.filter(Q(customer__name__icontains=word) |
                                         Q(name__icontains=word) |
                                         Q(contact_person__icontains=word))
        if order != '0':
            receivers = receivers.order_by(order)
        return receivers
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Отримувач', 1],
                              ['address', 'Адреса', 0],
                              ['contact_person', 'Контактна особа', 0],
                              ['phone', 'Телефон', 0]]
        context['search'] = True
        context['filter'] = []
        context['add_url'] = reverse('receiver_add')
        context['add_help_text'] = 'Додати адресата'
        context['header_main'] = 'Адресати'
        context['objects_count'] = Receiver.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ReceiverFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.ReceiverFilterForm(self.request.GET)

        return context


@method_decorator(login_required, name='dispatch')
class ReceiverCreate(CreateView):
    model = Receiver
    form_class = forms.ReceiverForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('receiver_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати адресат'
        context['back_btn_url'] = reverse('receiver_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class ReceiverUpdate(UpdateView):
    model = Receiver
    form_class = forms.ReceiverForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('receiver_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['receiver']
        context['header_main'] = 'Редагування ' + str(name)
        context['back_btn_url'] = reverse('receiver_delete', kwargs={'pk':name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class ReceiverDelete(DeleteView):
    model = Receiver
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('receiver_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        receiver = context['receiver']
        context['go_back_url'] = reverse('receiver_update', kwargs={'pk':receiver.pk})
        context['main_header'] = 'Видалити адресат?'
        context['header'] = 'Видалення адресату "' + str(receiver) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if obj.task_set.exists():
            context['objects'] = obj.sending_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class ProjectList(ListView):
    """ ListView for ProjectList.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Project
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15
    
    def get_queryset(self):
        project_types = Project.objects.annotate(url=Concat(F('pk'), Value('/change/')))\
            .annotate(net_price=ExpressionWrapper(Round(F('price')*F('net_price_rate')/100), output_field=DecimalField())).\
            values_list('project_type', 'customer__name', 'price_code', 'net_price', 'copies_count', 'active', 'url')
        search_string = self.request.GET.get('filter', '').split()
        customer = self.request.GET.get('customer', '0')
        order = self.request.GET.get('o', '0')
        for word in search_string:
            project_types = project_types.filter(project_type__icontains=word)
        if customer != '0':
            project_types = project_types.filter(customer=customer)
        if order != '0':
            project_types = project_types.order_by(order)
        return project_types
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['headers'] = [['project_type', 'Вид робіт', 1],
                              ['customer', 'Замовник', 0],
                              ['price_code', 'Пункт кошторису', 0],
                              ['net_price_rate', 'Вартість після вхідних витрат', 0],
                              ['copies_count', 'Кількість примірників', 0],
                              ['active', 'Активний', 0]]
        context['search'] = True
        context['filter'] = []
        context['add_url'] = reverse('project_type_add')
        context['add_help_text'] = 'Додати вид робіт'
        context['header_main'] = 'Види робіт'
        context['objects_count'] = Project.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ProjectFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.ProjectFilterForm(self.request.GET)
        
        return context


@method_decorator(login_required, name='dispatch')
class ProjectCreate(CreateView):
    model = Project
    form_class = forms.ProjectForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('project_type_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати вид робіт'
        context['back_btn_url'] = reverse('project_type_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class ProjectUpdate(UpdateView):
    model = Project
    form_class = forms.ProjectForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('project_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['project']
        context['header_main'] = 'Вид робіт'
        context['back_btn_url'] = reverse('project_type_delete', kwargs={'pk':name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class ProjectDelete(DeleteView):
    model = Project
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('project_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        project = context['project']
        context['go_back_url'] = reverse('project_type_update', kwargs={'pk':project.pk})
        context['main_header'] = 'Видалити вид робіт?'
        context['header'] = 'Видалення "' + str(project) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if obj.task_set.exists():
            context['objects'] = obj.task_set.all()
        return context
