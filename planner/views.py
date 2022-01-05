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
# from django.views.generic.dates import WeekArchiveView
from django.db.models import Q, F, Value, ExpressionWrapper, DecimalField, Func, Sum, Case, When
from django.db.models.functions import Concat
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.http import QueryDict
from django.conf.locale.uk import formats as uk_formats
from crum import get_current_user

from .context import context_accounter, context_pm, context_projector
from . import forms
from .models import Task, Deal, Employee, Project, Execution, Receiver, Sending, Order,\
                    IntTask, Customer, Company, Contractor

date_format = uk_formats.DATE_INPUT_FORMATS[0]


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 2)'


def subtasks_queryset_filter(request):
    exec_statuses = request.GET.getlist('exec_status', '0')
    executors = request.GET.getlist('executor', '0')
    companies = request.GET.getlist('company', '0')
    start_date = request.GET.get('start_date')
    finish_date = request.GET.get('finish_date')
    search_string = request.GET.get('filter', '').split()
    order = request.GET.get('o', '0')

    # create qs tasks
    tasks = Execution.objects.all().select_related('executor', 'task', 'task__deal')
    if request.user.is_superuser:
        pass
    else:
        query = Q()
        if request.user.groups.filter(name='Замовники').exists():
            query |= Q(task__deal__customer__user=request.user)
        if request.user.groups.filter(name='ГІПи').exists():
            query |= Q(task__owner=request.user.employee)
        if request.user.groups.filter(name='Проектувальники').exists():
            query |= Q(executor=request.user.employee)
        tasks = tasks.filter(query)

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
        finish_date_value = start_date_value + timedelta(days=14)
    tasks = tasks.filter(Q(planned_start__gte=start_date_value, planned_start__lte=finish_date_value) |
                         Q(planned_finish__gte=start_date_value, planned_finish__lte=finish_date_value) |
                         Q(planned_finish__lt=date.today()),
                         exec_status__in=[Execution.ToDo,
                                          Execution.InProgress,
                                          Execution.OnChecking]
                         ). \
                  exclude(task__exec_status__in=[Task.OnHold, Task.Canceled])
    for word in search_string:
        tasks = tasks.filter(Q(part_name__icontains=word) |
                             Q(task__object_code__icontains=word) |
                             Q(task__project_type__project_type__icontains=word) |
                             Q(task__object_address__icontains=word) |
                             Q(task__deal__number__icontains=word))
    if order != '0':
        tasks = tasks.order_by(order)
    else:
        tasks = tasks.order_by('planned_finish', 'planned_start')
    return tasks, start_date_value, finish_date_value


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


@method_decorator(login_required, name='dispatch')
class Dashboard(TemplateView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Замовники').exists():
            return redirect('task_list')
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.request.user.groups.filter(name='Бухгалтери').exists():
            return 'content_admin.html'
        if self.request.user.groups.filter(name='ГІПи').exists():
            return 'content_gip.html'
        return 'content_exec.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.groups.filter(name='Бухгалтери').exists():
            return {**context, **context_accounter(self.request.user)}
        if self.request.user.groups.filter(name='ГІПи').exists():
            return {**context, **context_pm(self.request.user)}
        return {**context, **context_projector(self.request.user)}


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
        search_string = self.request.GET.get('filter', '').split()
        customers = self.request.GET.getlist('customer', '0')
        companies = self.request.GET.getlist('company', '0')
        act_statuses = self.request.GET.getlist('act_status', '0')
        pay_statuses = self.request.GET.getlist('pay_status', '0')
        specific_status = self.request.GET.get('specific_status', '0')
        order = self.request.GET.get('o', '0')

        if specific_status == 'OP':
            deals = Deal.objects.overdue_payment()
        else:
            deals = Deal.objects.all()

        deals = deals.select_related('customer', 'company')

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
    queryset = Deal.objects.select_related('company', 'customer') \
                           .prefetch_related('task_set', 'task_set__project_type', 'task_set__owner')
    form_class = forms.DealForm
    context_object_name = 'deal'
    success_url = reverse_lazy('deal_list')

    def get_context_data(self, **kwargs):
        context = super(DealUpdate, self).get_context_data(**kwargs)
        if self.request.POST:
            context['tasks_formset'] = forms.TasksFormSet(self.request.POST, instance=self.object)
            context['actofacceptance_formset'] = forms.ActOfAcceptanceFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['payment_formset'] = forms.PaymentFormSet(self.request.POST, instance=self.object)
        else:
            context['tasks_formset'] = forms.TasksFormSet(instance=self.object, form_kwargs={'deal': self.object})
            context['actofacceptance_formset'] = forms.ActOfAcceptanceFormSet(instance=self.object)
            context['payment_formset'] = forms.PaymentFormSet(instance=self.object, form_kwargs={'deal': self.object})
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        tasks_formset = context['tasks_formset']
        actofacceptance_formset = context['actofacceptance_formset']
        payment_formset = context['payment_formset']
        if tasks_formset.is_valid() and actofacceptance_formset.is_valid() and payment_formset.is_valid():
            with transaction.atomic():
                actofacceptance_formset.instance = self.object
                actofacceptance_formset.save()
                payment_formset.instance = self.object
                payment_formset.save()
                form.save()
                tasks_formset.instance = self.object
                tasks_formset.save()
            if self.request.POST.get('save_add'):
                return redirect('deal_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='dispatch')
class DealCreate(CreateView):
    model = Deal
    form_class = forms.DealForm
    context_object_name = 'deal'
    success_url = reverse_lazy('deal_list')

    def form_valid(self, form):
        if form.is_valid():
            with transaction.atomic():
                self.object = form.save()
            if self.request.POST.get('save_add'):
                return redirect('deal_update', self.object.pk)
            else:
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
        tasks = Task.objects.all().select_related('project_type', 'owner', 'deal', 'deal__customer')
        # filter only customer tasks
        if self.request.user.groups.filter(name='Замовники').exists():
            tasks = tasks.filter(deal__customer__user=self.request.user)
        search_string = self.request.GET.get('filter', '').split()
        exec_statuses = self.request.GET.getlist('exec_status', '0')
        owners = self.request.GET.getlist('owner', '0')
        customers = self.request.GET.getlist('customer', '0')
        constructions = self.request.GET.getlist('construction', '0')
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
        if constructions != '0':
            tasks_union = Task.objects.none()
            for construction in constructions:
                tasks_segment = tasks.filter(construction=construction)
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
        if 'task_success_url' in self.request.session and \
                self.request.session['task_success_url'] == 'execution':
            return reverse_lazy('sprint_list')
        return reverse_lazy('task_list')

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
        if executors_formset.is_valid() and costs_formset.is_valid() and sending_formset.is_valid():
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
        if 'task_success_url' in self.request.session and \
                self.request.session['task_success_url'] == 'execution':
            return reverse_lazy('sprint_list')
        return reverse_lazy('task_list')


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
    template_name = "planner/subtask_sprint_list.html"
    context_object_name = 'tasks'
    paginate_by = 50
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            if self.request.session.get('execution_query_string'):
                query_string = QueryDict(self.request.session.get('execution_query_string')).copy()
                if 'start_date' in query_string:
                    del query_string['start_date']
                if 'finish_date' in query_string:
                    del query_string['finish_date']
                request.GET = query_string
                request.META['QUERY_STRING'] = self.request.session.get('execution_query_string')
        if request.user.has_perm('planner.view_execution'):
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_queryset(self):
        # filtering queryset
        queryset, _, _ = subtasks_queryset_filter(self.request)
        # return filtered queryset
        return queryset

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
        return redirect(reverse('sprint_list') + '?' + self.request.session.get('execution_query_string', ''))


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
class SubtaskDetail(DetailView):
    model = Execution
    success_url = reverse_lazy('home_page')

    def get_context_data(self, **kwargs):
        context = super(SubtaskDetail, self).get_context_data(**kwargs)
        execution = Execution.objects.get(pk=self.kwargs['pk'])
        context['executors'] = Execution.objects.filter(task=execution.task)
        context['sendings'] = Sending.objects.filter(task=execution.task)
        return context


@method_decorator(login_required, name='dispatch')
class InttaskDetail(DetailView):
    model = IntTask
    success_url = reverse_lazy('home_page')


@method_decorator(login_required, name='dispatch')
class ReceiverList(ListView):
    """ ListView for Receivers.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Receiver
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 15

    def get_queryset(self):
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
            project_types = project_types.filter(Q(project_type__icontains=word) |
                                                 Q(price_code__contains=word) |
                                                 Q(description__icontains=word))
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
        a_month_ago = date.today() - timedelta(days=30)
        # deals = Deal.objects.filter(customer=OuterRef('pk'), pay_status__in=[Deal.NotPaid, Deal.AdvancePaid]) \
        #                     .order_by().values('customer')
        # total_debit = deals.annotate(total=Sum(F('value'), output_field=DecimalField())).values('total')
        customers = Customer.objects.annotate(
            url=Concat(F('pk'), Value('/change/')),
            advance = Sum(Case(When(deal__pay_status=Deal.AdvancePaid, then=F('deal__value')), output_field=DecimalField(), default=0)),
            debit = Sum(Case(When(deal__pay_status=Deal.NotPaid, then=F('deal__value')), output_field=DecimalField(), default=0)),
            payments = Sum(Case(When(deal__pay_status=Deal.NotPaid, then=F('deal__payment__value')), output_field=DecimalField(), default=0)),
            ).values_list('name', 'debit', 'payments', 'url')

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
                              ['debit', 'Дебітрська заборгованість', 0],
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
            context['filter_form'] = forms.CustomerFilterForm(self.request.POST)
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
class СolleagueList(ListView):
    """ ListView for Сolleagues.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Employee
    template_name = "planner/colleague_list.html"
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
                                    .values_list('name', 'url')
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
class СolleagueDetail(DetailView):
    model = Employee
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
