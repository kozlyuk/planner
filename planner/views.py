from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic import FormView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.dates import WeekArchiveView
from django.db.models import Q, F, Value, ExpressionWrapper, DecimalField, Func
from django.db.models.functions import Concat
from django.db import transaction
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.http import HttpResponse, QueryDict
from django.conf.locale.uk import formats as uk_formats
from crum import get_current_user

from eventlog.models import Log
from planner import forms
from planner.models import Task, Deal, Employee, Project, Execution, Receiver, Sending, Order,\
    IntTask, News, Event, Customer, Company, Contractor

date_format = uk_formats.DATE_INPUT_FORMATS[0]


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
        objects = tasks.values(
            'object_code', 'object_address').order_by().distinct()
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
                object_lists.append([index, ptype['project_type__description'] + ' ' + object_list, 'послуга',
                                     count, round(price, 2), round(value, 2)])
        elif template == 'msz':
            object_lists = [[] for _ in range(len(objects))]
            for obj in range(len(objects)):
                index += 1
                object_lists[obj].append(
                    [objects[obj]['object_code'] + ' ' + objects[obj]['object_address']])
                for task in tasks.filter(object_code=objects[obj]['object_code'])\
                        .values('project_type__price_code', 'project_type__description', 'project_type__price'):
                    if task['project_type__price'] != 0:
                        price = round(task['project_type__price'] / 6 * 5, 2)
                        svalue += price
                    object_lists[obj].append(
                        [index, task['project_type__description'], 'шт.', 1, price, price])

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
        if request.user.is_superuser or request.user == employee.user or request.user == employee.head.user \
                or request.user.groups.filter(name='Бухгалтери').exists():
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

        bonuses = round(bonuses, 2)

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
        deals_div = int(actneed_deals_count / active_deals_count *
                        100) if active_deals_count > 0 else 0
        debtor_deals_div = int(
            debtor_deals_count / unpaid_deals_count * 100) if unpaid_deals_count > 0 else 0
        overdue_deals_count = len(overdue_deals)
        overdue_deals_div = int(
            overdue_deals_count / active_deals_count * 100) if active_deals_count > 0 else 0
    elif request.user.groups.filter(name='ГІПи').exists():
        td_tasks = Task.objects.filter(
            exec_status=Task.ToDo, owner__user=request.user).order_by('creation_date')
        ip_tasks = Task.objects.filter(
            exec_status=Task.InProgress, owner__user=request.user).order_by('creation_date')
        hd_tasks = Task.objects.filter(
            exec_status=Task.Done, owner__user=request.user).order_by('creation_date')
        sent_tasks = Task.objects.filter(owner__user=request.user, exec_status=Task.Sent,
                                         actual_finish__month=datetime.now().month,
                                         actual_finish__year=datetime.now().year)\
            .order_by('-actual_finish')
        td_tasks_count = td_tasks.count()
        ip_tasks_count = ip_tasks.count()
        hd_tasks_count = hd_tasks.count()
        sent_tasks_count = sent_tasks.count()
        active_tasks_count = Task.objects.filter(owner__user=request.user).exclude(
            exec_status=Task.Sent).count() + sent_tasks_count
        tasks_div = int(sent_tasks_count / active_tasks_count *
                        100) if active_tasks_count > 0 else 0
        overdue_tasks_count = Task.objects.filter(owner__user=request.user).exclude(exec_status=Task.Sent)\
                                          .exclude(deal__expire_date__gte=date.today(), planned_finish__isnull=True)\
                                          .exclude(deal__expire_date__gte=date.today(), planned_finish__gte=date.today())\
                                          .count()
        overdue_tasks_div = int(
            overdue_tasks_count / active_tasks_count * 100) if active_tasks_count > 0 else 0
        owner_productivity = request.user.employee.owner_productivity()
    else:
        td_executions = Execution.objects.filter(
            executor__user=request.user, exec_status=Execution.ToDo).order_by('creation_date')
        ip_executions = Execution.objects.filter(
            executor__user=request.user, exec_status=Execution.InProgress).order_by('creation_date')
        hd_executions = Execution.objects.filter(executor__user=request.user, exec_status=Execution.Done,
                                                 finish_date__month=datetime.now().month, finish_date__year=datetime.now().year)
        td_executions_count = td_executions.count()
        ip_executions_count = ip_executions.count()
        hd_executions_count = hd_executions.count()
        active_executions_count = Execution.objects.filter(executor__user=request.user)\
                                                   .exclude(exec_status=Execution.Done)\
                                                   .count() + hd_executions_count
        executions_div = int(hd_executions_count / active_executions_count *
                             100) if active_executions_count > 0 else 0
        overdue_executions_count = Execution.objects.filter(executor__user=request.user)\
                                            .exclude(exec_status=Execution.Done)\
                                            .exclude(task__deal__expire_date__gte=date.today(), task__planned_finish__isnull=True)\
                                            .exclude(task__deal__expire_date__gte=date.today(), task__planned_finish__gte=date.today())\
                                            .count()
        overdue_executions_div = int(
            overdue_executions_count / active_executions_count * 100) if active_executions_count > 0 else 0
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
    overdue_inttasks_div = int(
        overdue_inttasks_count / active_inttasks_count * 100) if active_inttasks_count > 0 else 0

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

    news = News.objects.exclude(actual_from__gt=date.today()).exclude(
        actual_to__lte=date.today()).order_by('-created')
    events = Event.objects.filter(
        next_date__isnull=False).order_by('next_date')
    activities = Log.objects.filter(user=request.user)[:50]

    if request.user.groups.filter(name='Бухгалтери').exists():
        return render(request, 'content_admin.html',
                      {
                          'employee': request.user.employee,
                          'actneed_deals': actneed_deals,
                          'debtor_deals': debtor_deals,
                          'overdue_deals': overdue_deals,
                          'inttasks': inttasks,
                          # 'td_inttasks': td_inttasks,
                          # 'ip_inttasks': ip_inttasks,
                          # 'hd_inttasks': hd_inttasks,
                          'actneed_deals_count': actneed_deals_count,
                          'active_deals_count': active_deals_count,
                          'deals_div': deals_div,
                          'debtor_deals_count': debtor_deals_count,
                          'unpaid_deals_count': unpaid_deals_count,
                          'debtor_deals_div': debtor_deals_div,
                          'overdue_deals_count': overdue_deals_count,
                          'overdue_deals_div': overdue_deals_div,
                          # 'hd_inttasks_count': hd_inttasks_count,
                          'active_inttasks_count': active_inttasks_count,
                          # 'inttasks_div': inttasks_div,
                          'overdue_inttasks_count': overdue_inttasks_count,
                          'overdue_inttasks_div': overdue_inttasks_div,
                          'exec_bonuses_cm': exec_bonuses_cm,
                          # 'exec_bonuses_pm': exec_bonuses_pm,
                          # 'exec_bonuses_ppm': exec_bonuses_ppm,
                          'owner_bonuses_cm': owner_bonuses_cm,
                          # 'owner_bonuses_pm': owner_bonuses_pm,
                          # 'owner_bonuses_ppm': owner_bonuses_ppm,
                          'inttask_bonuses_cm': inttask_bonuses_cm,
                          # 'inttask_bonuses_pm': inttask_bonuses_pm,
                          # 'inttask_bonuses_ppm': inttask_bonuses_ppm,
                          'total_bonuses_cm': total_bonuses_cm,
                          # 'total_bonuses_pm': total_bonuses_pm,
                          # 'total_bonuses_ppm': total_bonuses_ppm,
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
                          # 'td_inttasks': td_inttasks,
                          # 'ip_inttasks': ip_inttasks,
                          # 'hd_inttasks': hd_inttasks,
                          'td_tasks_count': td_tasks_count,
                          'ip_tasks_count': ip_tasks_count,
                          'hd_tasks_count': hd_tasks_count,
                          'sent_tasks_count': sent_tasks_count,
                          'active_tasks_count': active_tasks_count,
                          'tasks_div': tasks_div,
                          'overdue_tasks_count': overdue_tasks_count,
                          'overdue_tasks_div': overdue_tasks_div,
                          'owner_productivity': owner_productivity,
                          # 'hd_inttasks_count': hd_inttasks_count,
                          'active_inttasks_count': active_inttasks_count,
                          # 'inttasks_div': inttasks_div,
                          'overdue_inttasks_count': overdue_inttasks_count,
                          'overdue_inttasks_div': overdue_inttasks_div,
                          'exec_bonuses_cm': exec_bonuses_cm,
                          # 'exec_bonuses_pm': exec_bonuses_pm,
                          # 'exec_bonuses_ppm': exec_bonuses_ppm,
                          'owner_bonuses_cm': owner_bonuses_cm,
                          # 'owner_bonuses_pm': owner_bonuses_pm,
                          # 'owner_bonuses_ppm': owner_bonuses_ppm,
                          'inttask_bonuses_cm': inttask_bonuses_cm,
                          # 'inttask_bonuses_pm': inttask_bonuses_pm,
                          # 'inttask_bonuses_ppm': inttask_bonuses_ppm,
                          'total_bonuses_cm': total_bonuses_cm,
                          # 'total_bonuses_pm': total_bonuses_pm,
                          # 'total_bonuses_ppm': total_bonuses_ppm,
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
                          # 'td_inttasks': td_inttasks,
                          # 'ip_inttasks': ip_inttasks,
                          # 'hd_inttasks': hd_inttasks,
                          'td_executions_count': td_executions_count,
                          'ip_executions_count': ip_executions_count,
                          'hd_executions_count': hd_executions_count,
                          'active_executions_count': active_executions_count,
                          'executions_div': executions_div,
                          'overdue_executions_count': overdue_executions_count,
                          'overdue_executions_div': overdue_executions_div,
                          'productivity': productivity,
                          # 'hd_inttasks_count': hd_inttasks_count,
                          'active_inttasks_count': active_inttasks_count,
                          # 'inttasks_div': inttasks_div,
                          'overdue_inttasks_count': overdue_inttasks_count,
                          'overdue_inttasks_div': overdue_inttasks_div,
                          'exec_bonuses_cm': exec_bonuses_cm,
                          # 'exec_bonuses_pm': exec_bonuses_pm,
                          # 'exec_bonuses_ppm': exec_bonuses_ppm,
                          'owner_bonuses_cm': owner_bonuses_cm,
                          # 'owner_bonuses_pm': owner_bonuses_pm,
                          # 'owner_bonuses_ppm': owner_bonuses_ppm,
                          'inttask_bonuses_cm': inttask_bonuses_cm,
                          # 'inttask_bonuses_pm': inttask_bonuses_pm,
                          # 'inttask_bonuses_ppm': inttask_bonuses_ppm,
                          'total_bonuses_cm': total_bonuses_cm,
                          # 'total_bonuses_pm': total_bonuses_pm,
                          # 'total_bonuses_ppm': total_bonuses_ppm,
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
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('deal_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('deal_query_string', '')
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super(DealList, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_queryset(self):
        deals = Deal.objects.all()
        search_string = self.request.GET.get('filter', '').split()
        customers = self.request.GET.getlist('customer', '0')
        companies = self.request.GET.getlist('company', '0')
        act_statuses = self.request.GET.getlist('act_status', '0')
        pay_statuses = self.request.GET.getlist('pay_status', '0')
        order = self.request.GET.get('o', '0')
        for word in search_string:
            deals = deals.filter(Q(number__icontains=word) |
                                 Q(value__icontains=word))

        if customers != '0':
            deals_union = Deal.objects.none()
            for customer in customers:
                deals_part = deals.filter(customer=customer)
                deals_union = deals_union | deals_part
            deals = deals_union
        if companies != '0':
            deals_union = Deal.objects.none()
            for company in companies:
                deals_part = deals.filter(company=company)
                deals_union = deals_union | deals_part
            deals = deals_union
        if act_statuses != '0':
            deals_union = Deal.objects.none()
            for act_status in act_statuses:
                deals_part = deals.filter(act_status=act_status)
                deals_union = deals_union | deals_part
            deals = deals_union
        if pay_statuses != '0':
            deals_union = Deal.objects.none()
            for pay_status in pay_statuses:
                deals_part = deals.filter(pay_status=pay_status)
                deals_union = deals_union | deals_part
            deals = deals_union
        if order != '0':
            deals = deals.order_by(order)
        return deals

    def get_context_data(self, **kwargs):
        context = super(DealList, self).get_context_data(**kwargs)
        context['deals_count'] = Deal.objects.all().count()
        context['deals_filtered'] = self.object_list.count()
        context['submit_icon'] = format_html('<i class="fa fa-filter"></i>')
        context['submit_button_text'] = 'Пошук'
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
    success_url = reverse_lazy('deal_list')

    def get_context_data(self, **kwargs):
        context = super(DealUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = forms.TasksFormSet(
                self.request.POST, instance=self.object)
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
    success_url = reverse_lazy('deal_list')

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
    success_url = reverse_lazy('deal_list')

    def get_context_data(self, **kwargs):
        context = super(DealDelete, self).get_context_data(**kwargs)
        if self.object.task_set.exists():
            context['tasks'] = self.object.task_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class TaskList(ListView):
    model = Task
    context_object_name = 'tasks'  # Default: object_list
    paginate_by = 50
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('task_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('task_query_string', '')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        tasks = Task.objects.all()
        search_string = self.request.GET.get('filter', '').split()
        exec_statuses = self.request.GET.getlist('exec_status', '0')
        owners = self.request.GET.getlist('owner', '0')
        customers = self.request.GET.getlist('customer', '0')
        order = self.request.GET.get('o', '0')
        for word in search_string:
            tasks = tasks.filter(Q(object_code__icontains=word) |
                                 Q(object_address__icontains=word) |
                                 Q(deal__number__icontains=word) |
                                 Q(project_type__price_code__icontains=word) |
                                 Q(project_type__project_type__icontains=word))
        if exec_statuses != '0':
            tasks_union = Task.objects.none()
            for status in exec_statuses:
                tasks_segment = tasks.filter(exec_status=status)
                tasks_union = tasks_union | tasks_segment
            tasks = tasks_union
        if owners != '0':
            tasks_union = Task.objects.none()
            for owner in owners:
                tasks_segment = tasks.filter(owner=owner)
                tasks_union = tasks_union | tasks_segment
            tasks = tasks_union
        if customers != '0':
            tasks_union = Task.objects.none()
            for customer in customers:
                tasks_segment = tasks.filter(deal__customer=customer)
                tasks_union = tasks_union | tasks_segment
            tasks = tasks_union
        if order != '0':
            tasks = tasks.order_by(order)
        else:
            tasks = tasks.order_by('-creation_date', '-deal', 'object_code')
        return tasks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks_count'] = Task.objects.all().count()
        context['tasks_filtered'] = self.object_list.count()
        context['form_action'] = reverse('task_list')
        context['submit_icon'] = format_html('<i class="fa fa-filter"></i>')
        context['submit_button_text'] = 'Пошук'
        self.request.session['task_query_string'] = self.request.META['QUERY_STRING']
        self.request.session['task_success_url'] = 'task'
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
        if self.request.session['task_success_url'] == 'task':
            return reverse_lazy('task_list')
        return reverse_lazy('sprint_list')

    def get_context_data(self, **kwargs):
        context = super(TaskUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = forms.ExecutorsFormSet(
                self.request.POST, instance=self.object)
            context['costs_formset'] = forms.CostsFormSet(
                self.request.POST, instance=self.object)
            context['sending_formset'] = forms.SendingFormSet(
                self.request.POST, instance=self.object)
        else:
            context['executors_formset'] = forms.ExecutorsFormSet(
                instance=self.object)
            context['costs_formset'] = forms.CostsFormSet(instance=self.object)
            context['sending_formset'] = forms.SendingFormSet(
                instance=self.object)
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
    success_url = reverse_lazy('task_list')

    def get_context_data(self, **kwargs):
        context = super(TaskCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = forms.ExecutorsFormSet(
                self.request.POST)
            context['costs_formset'] = forms.CostsFormSet(self.request.POST)
            context['sending_formset'] = forms.SendingFormSet(
                self.request.POST)
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
        if self.request.session['task_success_url'] == 'task':
            return reverse_lazy('task_list')
        return reverse_lazy('sprint_list')


@method_decorator(login_required, name='dispatch')
class TaskExchange(FormView):
    template_name = 'planner/task_exchange.html'
    form_class = forms.TaskExchangeForm
    success_url = reverse_lazy('task_list')

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
class SprintList(ListView):
    model = Execution
#    date_field = "pub_date"
#    week_format = "%W"
#    allow_future = True

    template_name = "planner/subtask_sprint_list.html"
    context_object_name = 'tasks'  # Default: object_list
    paginate_by = 50
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('execution_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('execution_query_string', '')
        if request.user.is_superuser or request.user.groups.filter(name='ГІПи').exists() or \
                request.user.groups.filter(name='Проектувальники').exists():
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied

    def get_queryset(self):
        tasks = Execution.objects.all()
        exec_statuses = self.request.GET.getlist('exec_status', '0')
        executors = self.request.GET.getlist('executor', '0')
        companies = self.request.GET.getlist('company', '0')
        start_date = self.request.GET.get('start_date')
        finish_date = self.request.GET.get('finish_date')
        search_string = self.request.GET.get('filter', '').split()
        order = self.request.GET.get('o', '0')

        if self.request.user.is_superuser:
            pass
        elif self.request.user.groups.filter(name='ГІПи').exists():
            tasks = tasks.filter(task__owner=self.request.user.employee)
        elif self.request.user.groups.filter(name='Проектувальники').exists():
            tasks = tasks.filter(executor=self.request.user.employee)

        if exec_statuses != '0':
            tasks_union = Task.objects.none()
            for status in exec_statuses:
                tasks_part = tasks.filter(exec_status=status)
                tasks_union = tasks_union | tasks_part
            tasks = tasks_union
        if executors != '0':
            tasks_union = Task.objects.none()
            for executor in executors:
                tasks_part = tasks.filter(executor=executor)
                tasks_union = tasks_union | tasks_part
            tasks = tasks_union
        if companies != '0':
            tasks_union = Task.objects.none()
            for company in companies:
                tasks_part = tasks.filter(task__deal__company=company)
                tasks_union = tasks_union | tasks_part
            tasks = tasks_union
        if start_date:
            start_date_value = datetime.strptime(start_date, date_format)
        else:
            start_date_value = date.today() - timedelta(days=date.today().weekday())
        if finish_date:
            finish_date_value = datetime.strptime(finish_date, date_format)
        else:
            finish_date_value = start_date_value + timedelta(days=4)
        tasks = tasks.filter(Q(planned_start__gte=start_date_value, planned_start__lte=finish_date_value) |
                             Q(planned_finish__gte=start_date_value, planned_finish__lte=finish_date_value))
        for word in search_string:
            tasks = tasks.filter(Q(part_name__icontains=word) |
                                 Q(task__object_code__icontains=word) |
                                 Q(task__project_type__project_type__icontains=word) |
                                 Q(task__object_address__icontains=word) |
                                 Q(task__deal__number__icontains=word))
        if order != '0':
            tasks = tasks.order_by(order)
        else:
            tasks = tasks.order_by('-planned_finish', 'task__object_code')
        return tasks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks_count'] = Execution.objects.all().count()
        context['form_action'] = reverse('sprint_list')
        context['tasks_filtered'] = self.object_list.count()
        context['submit_icon'] = format_html('<i class="fas fa-filter"></i>')
        context['submit_button_text'] = 'Застосувати фільтр'
        self.request.session['execution_query_string'] = self.request.META['QUERY_STRING']
        self.request.session['task_success_url'] = 'execution'
        if self.request.POST:
            context['filter_form'] = forms.SprintFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.SprintFilterForm(self.request.GET)
        return context


class ExecutionStatusChange(View):
    """ View change Execution exec_status to given in url """

    def dispatch(self, request, *args, **kwargs):
        obj = Execution.objects.filter(pk=kwargs['pk']).first()
        if kwargs['status'] in dict(Execution.EXEC_STATUS_CHOICES):
            if request.user.is_superuser or request.user == obj.task.owner.user:
                return super().dispatch(request, *args, **kwargs)
            if request.user == obj.executor.user:
                if kwargs['status'] != Execution.Done:
                    return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        obj = Execution.objects.filter(pk=kwargs['pk']).first()
        if obj:
            obj.exec_status = kwargs['status']
            obj.save()
        return redirect(reverse('sprint_list') + '?' +  self.request.session.get('execution_query_string', ''))


# @method_decorator(login_required, name='dispatch')
# class TaskRegistry(FormView):
#     template_name = 'planner/task_registry.html'
#     form_class = TaskRegistryForm
#
#     def get_success_url(self):
#         return reverse_lazy('task_list') + '?' + self.request.session.get('task_query_string', '')
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
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Отримувач', 1],
                              ['address', 'Адреса', 0],
                              ['contact_person', 'Контактна особа', 0],
                              ['phone', 'Телефон', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_receiver'):
            context['add_url'] = reverse('receiver_add')
            context['add_help_text'] = 'Додати адресата'
        context['header_main'] = 'Адресати'
        context['objects_count'] = Receiver.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ReceiverFilterForm(
                self.request.POST)
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
        context['back_btn_url'] = reverse(
            'receiver_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class ReceiverDelete(DeleteView):
    model = Receiver
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('receiver_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receiver = context['receiver']
        context['go_back_url'] = reverse(
            'receiver_update', kwargs={'pk': receiver.pk})
        context['main_header'] = 'Видалити адресат?'
        context['header'] = 'Видалення адресату "' + \
            str(receiver) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.task_set.exists():
            context['objects'] = self.object.sending_set.all()
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
            .annotate(net_price=ExpressionWrapper(Round(F('price')*F('net_price_rate')/100),
                                                  output_field=DecimalField())).\
            values_list('project_type', 'customer__name', 'price_code',
                        'net_price', 'copies_count', 'active', 'url')
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
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['project_type', 'Вид робіт', 1],
                              ['customer', 'Замовник', 0],
                              ['price_code', 'Пункт кошторису', 0],
                              ['net_price_rate', 'Вартість після вхідних витрат', 0],
                              ['copies_count', 'Кількість примірників', 0],
                              ['active', 'Активний', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_project'):
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
        context['back_btn_url'] = reverse(
            'project_type_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class ProjectDelete(DeleteView):
    model = Project
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('project_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = context['project']
        context['go_back_url'] = reverse(
            'project_type_update', kwargs={'pk': project.pk})
        context['main_header'] = 'Видалити вид робіт?'
        context['header'] = 'Видалення "' + \
            str(project) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.task_set.exists():
            context['objects'] = self.object.task_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class CustomerList(ListView):
    """ ListView for CustomerList.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Customer
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15

    def get_queryset(self):
        customers = Customer.objects.annotate(url=Concat(F('pk'), Value('/change/')))\
            .values_list('name', 'url')
        search_string = self.request.GET.get('filter', '').split()
        order = self.request.GET.get('o', '0')
        for word in search_string:
            customers = customers.filter(Q(name__icontains=word))
        if order != '0':
            customers = customers.order_by(order)
        return customers

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Назва', 1],
                              ['credit_calc', 'Авансові платежі', 0],
                              ['debit_calc', 'Дебітрська заборгованість', 0],
                              ['expect_calc', 'Не виконано та не оплачено', 0],
                              ['completed_calc', 'Виконано та оплачено', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_customer'):
            context['add_url'] = reverse('customer_add')
            context['add_help_text'] = 'Додати замовника'
        context['header_main'] = 'Замовники'
        context['objects_count'] = Customer.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.CustomerFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.CustomerFilterForm(self.request.GET)

        return context


@method_decorator(login_required, name='dispatch')
class CustomerCreate(CreateView):
    model = Customer
    form_class = forms.CustomerForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати замовника'
        context['back_btn_url'] = reverse('customer_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class CustomerUpdate(UpdateView):
    model = Customer
    form_class = forms.CustomerForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['customer']
        context['header_main'] = 'Замовник: ' + str(name)
        context['back_btn_url'] = reverse(
            'customer_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class CustomerDelete(DeleteView):
    model = Customer
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('customer_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = context['customer']
        context['go_back_url'] = reverse(
            'customer_update', kwargs={'pk': customer.pk})
        context['main_header'] = 'Видалити замовника?'
        context['header'] = 'Видалення "' + \
            str(customer) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.project_set.exists():
            context['objects'] = self.object.project_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class CompanyList(ListView):
    """ ListView for CompanyList.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Company
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15

    def get_queryset(self):
        companies = Company.objects.annotate(url=Concat(F('pk'), Value('/change/')))\
            .values_list('name', 'url')
        search_string = self.request.GET.get('filter', '').split()
        order = self.request.GET.get('o', '0')
        for word in search_string:
            companies = companies.filter(Q(name__icontains=word))
        if order != '0':
            companies = companies.order_by(order)
        return companies

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Назва', 1],
                              ['turnover_calc', 'Оборот', 0],
                              ['costs_calc', 'Витрати', 0],
                              ['bonuses_calc', 'Бонуси', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_company'):
            context['add_url'] = reverse('company_add')
            context['add_help_text'] = 'Додати компанію'
        context['header_main'] = 'Компанії'
        context['objects_count'] = Company.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.CompanyFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.CompanyFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class CompanyCreate(CreateView):
    model = Company
    form_class = forms.CompanyForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('company_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати команію'
        context['back_btn_url'] = reverse('company_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class CompanyUpdate(UpdateView):
    model = Company
    form_class = forms.CompanyForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('company_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['company']
        context['header_main'] = 'Компанія: ' + str(name)
        context['back_btn_url'] = reverse(
            'company_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class CompanyDelete(DeleteView):
    model = Company
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('company_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = context['company']
        context['go_back_url'] = reverse(
            'company_update', kwargs={'pk': company.pk})
        context['main_header'] = 'Видалити компанію?'
        context['header'] = 'Видалення "' + \
            str(company) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.deal_set.exists():
            context['objects'] = self.object.deal_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class СolleaguesList(ListView):
    """ ListView for Сolleagues.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Employee
    template_name = "planner/colleagues_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 18

    def get_queryset(self):
        employees = Employee.objects.filter(user__is_active=True)\
                                    .exclude(name__startswith='Аутсорсинг') \
                                    .order_by('name')\
                                    .annotate(url=Concat(F('pk'), Value('/detail/')))\
                                    .values_list('avatar', 'name', 'url', 'position')
        search_string = self.request.GET.get('filter', '').split()
        for word in search_string:
            employees = employees.filter(Q(name__icontains=word))
        return employees

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_employee'):
            context['add_url'] = reverse('employee_add')
            context['add_help_text'] = 'Додати працівника'
        context['header_main'] = 'Колеги'
        context['objects_count'] = Employee.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.EmployeeFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.EmployeeFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class EmployeeList(ListView):
    """ ListView for Employee.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Employee
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 18

    def get_queryset(self):
        employees = Employee.objects.order_by('-user__is_active', 'name')\
                                    .annotate(url=Concat(F('pk'), Value('/change/')))\
                                    .values_list('name',  'url')
        search_string = self.request.GET.get('filter', '').split()
        for word in search_string:
            employees = employees.filter(Q(name__icontains=word))
        return employees

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'ПІБ', 1],
                              ['owner_count', 'Керівник проектів', 0],
                              ['task_count', 'Виконавець в проектах', 0],
                              ['inttask_count', 'Завдання', 0],
                              ['total_bonuses', 'Бонуси', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_employee'):
            context['add_url'] = reverse('employee_add')
            context['add_help_text'] = 'Додати працівника'
        context['header_main'] = 'Працівники'
        context['objects_count'] = Employee.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.EmployeeFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.EmployeeFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class СolleaguesDetail(DetailView):
    model = Employee
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super(СolleaguesDetail, self).get_context_data(**kwargs)
        return context


@method_decorator(login_required, name='dispatch')
class EmployeeUpdate(UpdateView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists() or \
                request.user.groups.filter(name='Секретарі').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    model = Employee
    form_class = forms.EmployeeForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('employee_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Користувач: ' + str(self.object.name)
        return context


@method_decorator(login_required, name='dispatch')
class EmployeeSelfUpdate(UpdateView):
    model = Employee
    form_class = forms.EmployeeSelfUpdateForm
    success_url = reverse_lazy('home_page')

    def get_object(self):
        return Employee.objects.get(user=get_current_user())


@method_decorator(login_required, name='dispatch')
class EmployeeCreate(CreateView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    model = Employee
    form_class = forms.EmployeeForm
    template_name = "planner/employee_create.html"
    success_url = reverse_lazy('employee_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати працівника'
        context['back_btn_url'] = reverse('employee_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class ContractorList(ListView):
    """ ListView for Contractor.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Contractor
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15

    def get_queryset(self):  # todo args url
        contractors = Contractor.objects.annotate(url=Concat(F('pk'), Value('/change/'))).\
            values_list('name', 'active', 'url')
        search_string = self.request.GET.get('filter', '').split()
        order = self.request.GET.get('o', '0')
        for word in search_string:
            contractors = contractors.filter(Q(name__icontains=word))
        if order != '0':
            contractors = contractors.order_by(order)
        return contractors

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Назва', 1],
                              ['advance_calc', 'Авансові платежі', 0],
                              ['credit_calc', 'Кредиторська заборгованість', 0],
                              ['expect_calc', 'Не виконано та не оплачено', 0],
                              ['completed_calc', 'Виконано та оплачено', 0],
                              ['active', 'Активний', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_contractor'):
            context['add_url'] = reverse('contractor_add')
            context['add_help_text'] = 'Додати підрядника'
        context['header_main'] = 'Підрядники'
        context['objects_count'] = Contractor.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ContractorFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.ContractorFilterForm(
                self.request.GET)

        return context


@method_decorator(login_required, name='dispatch')
class ContractorCreate(CreateView):
    model = Contractor
    form_class = forms.ContractorForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('contractor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати підрядника'
        context['back_btn_url'] = reverse('contractor_list')
        context['back_btn_text'] = 'Відміна'
        return context


@method_decorator(login_required, name='dispatch')
class ContractorUpdate(UpdateView):
    model = Contractor
    form_class = forms.ContractorForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('contractor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['contractor']
        context['header_main'] = 'Редагування ' + str(name)
        context['back_btn_url'] = reverse(
            'contractor_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        return context


@method_decorator(login_required, name='dispatch')
class ContractorDelete(DeleteView):
    model = Contractor
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('contractor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor = context['contractor']
        context['go_back_url'] = reverse(
            'contractor_update', kwargs={'pk': contractor.pk})
        context['main_header'] = 'Видалити адресат?'
        context['header'] = 'Видалення підрядника "' + \
            str(contractor) + \
            '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.order_set.exists():
            context['objects'] = self.object.order_set.all()
        return context
