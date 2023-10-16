from django.contrib.auth.decorators import login_required, user_passes_test

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
from django.db.models import Q, F, Value, ExpressionWrapper, DecimalField, Func, Sum, Case, When, CharField, DurationField
from django.db.models.functions import Concat, Coalesce
from django.db import transaction
from django.core.exceptions import PermissionDenied

from django.utils.html import format_html
from django.http import QueryDict
from crum import get_current_user
from bootstrap_modal_forms.generic import BSModalUpdateView

from .context import context_accounter, context_pm, context_projector
from . import forms
from .models import Task, Deal, Employee, Project, Execution, Receiver, Sending, Order,\
                    Contractor, SubTask, ActOfAcceptance, IntTask, Customer, Company, Plan
from .filters import *
from notice.models import Comment, create_comment
from eventlog.models import Log


is_staff = user_passes_test(lambda u: u.is_staff)

class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 2)'


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
            return redirect('sprint_list')
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


@method_decorator(is_staff, name='dispatch')
class DealList(ListView):
    model = Deal
    context_object_name = 'deals'  # Default: object_list
    paginate_by = 35
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('deal_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('deal_query_string', '')
        if request.user.is_superuser or request.user.groups.filter(name__in=['Бухгалтери', 'Секретарі']).exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_queryset(self):
        # filtering queryset
        queryset = deal_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = super(DealList, self).get_context_data(**kwargs)
        context['deals_count'] = Deal.objects.all().count()
        context['deals_filtered'] = self.object_list.count()
        context['submit_icon'] = format_html('<i class="fa fa-filter"></i>')
        context['submit_button_text'] = 'Застосувати фільтр'
        self.request.session['deal_query_string'] = self.request.META['QUERY_STRING']
        if self.request.POST:
            context['filter_form'] = forms.DealFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.DealFilterForm(self.request.GET)
        return context


@method_decorator(is_staff, name='dispatch')
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
            context['invoice_formset'] = forms.InvoiceFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            owners = Employee.objects.filter(user__groups__name__contains="ГІПи", user__is_active=True)
            project_types = Project.objects.filter(customer=self.object.customer, active=True)
            acts = ActOfAcceptance.objects.filter(deal=self.object)
            context['comments'] = Comment.objects.filter(content_type__model='Deal',
                                                         object_id=self.object.pk
                                                         )
            context['activities'] = Log.objects.filter(content_type__model='Deal',
                                                       object_id=self.object.pk
                                                       )
            context['tasks_formset'] = forms.TasksFormSet(
                instance=self.object, form_kwargs={'method': self.request.method,
                                                   'owners': owners,
                                                   'project_types': project_types,
                                                   'acts': acts}
                                                   )
            context['actofacceptance_formset'] = forms.ActOfAcceptanceFormSet(instance=self.object)
            context['payment_formset'] = forms.PaymentFormSet(instance=self.object, form_kwargs={'acts': acts})
            context['invoice_formset'] = forms.InvoiceFormSet(instance=self.object, form_kwargs={'acts': acts})
        return context

    def form_valid(self, form):
        # create comment if comment modal form was submitted
        if self.request.POST.get('comment_add'):
            comment_text = form.data.get('text')
            create_comment(get_current_user(), self.object, comment_text)
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_update'):
            comment_id = form.data.get('comment_update')
            comment = Comment.objects.get(pk=comment_id)
            comment.text = form.data.get('text')
            comment.save()
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_delete'):
            comment_id = form.data.get('comment_delete')
            comment = Comment.objects.get(pk=comment_id)
            comment.delete()
            return redirect(self.request.META['HTTP_REFERER'])

        context = self.get_context_data()
        tasks_formset = context['tasks_formset']
        actofacceptance_formset = context['actofacceptance_formset']
        payment_formset = context['payment_formset']
        invoice_formset = context['invoice_formset']
        if tasks_formset.is_valid() and actofacceptance_formset.is_valid() \
            and payment_formset.is_valid() and invoice_formset.is_valid():
            with transaction.atomic():
                actofacceptance_formset.instance = self.object
                actofacceptance_formset.save()
                payment_formset.instance = self.object
                payment_formset.save()
                invoice_formset.instance = self.object
                invoice_formset.save()
                form.save()
                tasks_formset.instance = self.object
                tasks_formset.save()
            if self.request.POST.get('save_add'):
                return redirect('deal_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class DealCreate(CreateView):
    model = Deal
    form_class = forms.DealForm
    context_object_name = 'deal'
    success_url = reverse_lazy('deal_list')

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()
            if self.request.POST.get('save_add'):
                return redirect('deal_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
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
    paginate_by = 35
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('task_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('task_query_string', '')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # filtering queryset
        queryset = task_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks_count'] = Task.objects.all().count()
        context['tasks_filtered'] = self.object_list.count()
        context['form_action'] = reverse('task_list')
        context['submit_icon'] = format_html('<i class="fa fa-filter"></i>')
        context['submit_button_text'] = 'Застосувати фільтр'
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
        context = super().get_context_data(**kwargs)
        context['comments'] = Comment.objects.filter(content_type__model='Task',
                                                     object_id=self.kwargs['pk']
                                                     )
        context['executors'] = Execution.objects.filter(task=self.kwargs['pk'])
        context['costs'] = Order.objects.filter(task=self.kwargs['pk'])
        context['sendings'] = Sending.objects.filter(task=self.kwargs['pk'])
        return context


@method_decorator(is_staff, name='dispatch')
class TaskUpdate(UpdateView):
    model = Task
    form_class = forms.TaskForm

    def get_success_url(self):
        if 'task_success_url' in self.request.session and \
                self.request.session['task_success_url'] == 'execution':
            return reverse_lazy('sprint_list')
        return reverse_lazy('task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['executors_formset'] = forms.ExecutorsFormSet(self.request.POST, instance=self.object)
            context['costs_formset'] = forms.CostsFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['sending_formset'] = forms.SendingFormSet(self.request.POST, instance=self.object)
        else:
            employees = Employee.objects.filter(user__is_active=True)
            subtasks = SubTask.objects.filter(project_type=self.object.project_type).order_by('name')
            contractors = Contractor.objects.filter(active=True)
            context['comments'] = Comment.objects.filter(content_type__model='Task',
                                                         object_id=self.object.pk
                                                         )
            context['activities'] = Log.objects.filter(content_type__model='Task',
                                                       object_id=self.object.pk
                                                       )
            context['executors_formset'] = forms.ExecutorsFormSet(
                instance=self.object, form_kwargs={'method': self.request.method,
                                                   'employees': employees,
                                                   'subtasks': subtasks}
                                                   )
            context['costs_formset'] = forms.CostsFormSet(
                instance=self.object, form_kwargs={'method': self.request.method,
                                                   'contractors': contractors,
                                                   'subtasks': subtasks}
                                                   )
            context['sending_formset'] = forms.SendingFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        # create comment if comment modal form was submitted
        if self.request.POST.get('comment_add'):
            comment_text = form.data.get('text')
            create_comment(get_current_user(), self.object, comment_text)
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_update'):
            comment_id = form.data.get('comment_update')
            comment = Comment.objects.get(pk=comment_id)
            comment.text = form.data.get('text')
            comment.save()
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_delete'):
            comment_id = form.data.get('comment_delete')
            comment = Comment.objects.get(pk=comment_id)
            comment.delete()
            return redirect(self.request.META['HTTP_REFERER'])

        context = self.get_context_data()
        executors_formset = context['executors_formset']
        costs_formset = context['costs_formset']
        sending_formset = context['sending_formset']
        if executors_formset.is_valid() and costs_formset.is_valid() and sending_formset.is_valid():
            with transaction.atomic():
                executors_formset.instance = self.object
                executors_formset.save()
                costs_formset.instance = self.object
                costs_formset.save()
                sending_formset.instance = self.object
                sending_formset.save()
                form.save()
            if self.request.POST.get('save_add'):
                return redirect('task_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class TaskCreate(CreateView):
    model = Task
    form_class = forms.TaskForm
    success_url = reverse_lazy('task_list')

    def form_valid(self, form):
        context = self.get_context_data()
        if form.is_valid():
            self.object = form.save()
            if self.request.POST.get('save_add'):
                return redirect('task_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class TaskDelete(DeleteView):
    model = Task

    def get_success_url(self):
        if 'task_success_url' in self.request.session and \
                self.request.session['task_success_url'] == 'execution':
            return reverse_lazy('sprint_list')
        return reverse_lazy('task_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.execution_set.exists():
            context['executions'] = self.object.execution_set.all()
        return context


@method_decorator(is_staff, name='dispatch')
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
                deal.save()
            deal_new.save()
        return super(TaskExchange, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class SprintList(ListView):
    model = Execution
    template_name = "planner/subtask_sprint_list.html"
    context_object_name = 'tasks'
    paginate_by = 32
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        query_string = self.request.session.get('execution_query_string')
        if request.GET == {} and query_string:
            request.GET = request.GET.copy()
            request.GET = QueryDict(query_string)
            request.META['QUERY_STRING'] = query_string
        #         query_string = QueryDict(query_string).copy()
        #         if 'actual_start' in query_string:
        #             del query_string['actual_start']
        #         if 'actual_finish' in query_string:
        #             del query_string['actual_finish']

        if request.user.has_perm('planner.view_execution'):
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_queryset(self):
        # filtering queryset
        queryset, _, _ = execuition_queryset_filter(self.request.user, self.request.GET)
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


@method_decorator(is_staff, name='dispatch')
class ExecutionStatusChange(View):
    """ View change Execution exec_status to given in url """

    def dispatch(self, request, *args, **kwargs):
        try:
            obj = Execution.objects.get(pk=kwargs['pk'])
        except:
            raise Execution.DoesNotExist

        if kwargs['status'] in dict(Execution.EXEC_STATUS_CHOICES):
            if request.user == obj.executor.user and (kwargs['status'] != Execution.Done or not obj.subtask.check_required):
                return super().dispatch(request, *args, **kwargs)
            if request.user.is_superuser or request.user == obj.task.owner.user:
                return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


    def get(self, request, *args, **kwargs):
        execution = Execution.objects.get(pk=kwargs['pk'])
        execution.exec_status = kwargs['status']
        execution.save()
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


@method_decorator(is_staff, name='dispatch')
class SubtaskDetail(DetailView):
    model = Execution
    success_url = reverse_lazy('home_page')

    def get_context_data(self, **kwargs):
        context = super(SubtaskDetail, self).get_context_data(**kwargs)
        execution = Execution.objects.get(pk=self.kwargs['pk'])
        context['executors'] = Execution.objects.filter(task=execution.task)
        context['sendings'] = Sending.objects.filter(task=execution.task)
        return context


@method_decorator(is_staff, name='dispatch')
class OrderList(ListView):
    model = Order
    context_object_name = 'orders'  # Default: object_list
    paginate_by = 35
    success_url = reverse_lazy('home_page')

    def dispatch(self, request, *args, **kwargs):
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('order_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('order_query_string', '')
        if request.user.is_superuser or request.user.has_perm('planner.view_order'):
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_queryset(self):
        # filtering queryset
        queryset = order_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orders_count'] = Order.objects.all().count()
        context['orders_filtered'] = self.object_list.count()
        context['total_value'] = self.object_list.aggregate(Sum('value'))['value__sum'] or 0
        context['submit_icon'] = format_html('<i class="fa fa-filter"></i>')
        context['submit_button_text'] = 'Застосувати фільтр'
        self.request.session['order_query_string'] = self.request.META['QUERY_STRING']
        if self.request.POST:
            context['filter_form'] = forms.OrderFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.OrderFilterForm(self.request.GET)
        return context


@method_decorator(is_staff, name='dispatch')
class OrderUpdate(UpdateView):
    queryset = Order.objects.select_related('task', 'subtask') \
                            .prefetch_related('orderpayment_set')
    form_class = forms.OrderForm
    context_object_name = 'order'
    success_url = reverse_lazy('order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['payment_formset'] = forms.OrderPaymentFormSet(self.request.POST, instance=self.object)
        else:
            context['comments'] = Comment.objects.filter(content_type__model='Order',
                                                         object_id=self.object.pk
                                                         )
            context['activities'] = Log.objects.filter(content_type__model='Order',
                                                       object_id=self.object.pk
                                                       )
            context['payment_formset'] = forms.OrderPaymentFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        # create comment if comment modal form was submitted
        if self.request.POST.get('comment_add'):
            comment_text = form.data.get('text')
            create_comment(get_current_user(), self.object, comment_text)
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_update'):
            comment_id = form.data.get('comment_update')
            comment = Comment.objects.get(pk=comment_id)
            comment.text = form.data.get('text')
            comment.save()
            return redirect(self.request.META['HTTP_REFERER'])

        # update comment if comment modal form was submitted
        if self.request.POST.get('comment_delete'):
            comment_id = form.data.get('comment_delete')
            comment = Comment.objects.get(pk=comment_id)
            comment.delete()
            return redirect(self.request.META['HTTP_REFERER'])

        context = self.get_context_data()
        payment_formset = context['payment_formset']
        if payment_formset.is_valid():
            with transaction.atomic():
                payment_formset.instance = self.object
                payment_formset.save()
                form.save()
            if self.request.POST.get('save_add'):
                return redirect('order_update', self.object.pk)
            elif self.request.POST.get('copy'):
                return redirect('order_copy', self.object.pk)
            elif self.request.POST.get('approve'):
                form.instance.approve()
            elif self.request.POST.get('cancel_approval'):
                form.instance.cancel_approval()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class OrderCreate(CreateView):
    model = Order
    form_class = forms.OrderForm
    context_object_name = 'order'
    success_url = reverse_lazy('order_list')

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()
            if self.request.POST.get('save_add'):
                return redirect('order_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class OrderCopy(UpdateView):
    model = Order
    form_class = forms.OrderForm
    context_object_name = 'order'
    success_url = reverse_lazy('order_list')

    def get_object(self):
        order = Order.objects.get(pk=self.kwargs['pk'])
        order.pk = None
        order.pay_status = Order.NotPaid
        order.pay_date = None
        order.approved_date = None
        order.approved_by = None
        order.invoice = None
        return order

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()
            if self.request.POST.get('save_add'):
                return redirect('order_update', self.object.pk)
            else:
                return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class OrderDelete(DeleteView):
    model = Order
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = context['order']
        context['go_back_url'] = reverse('receiver_update', kwargs={'pk': order.pk})
        context['main_header'] = 'Видалити замовлення?'
        context['header'] = 'Видалення замовлення "' + \
            str(order) + '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.orderpayment_set.exists():
            context['objects'] = self.object.orderpayment_set.all()
        return context


@method_decorator(is_staff, name='dispatch')
class OrderApprove(View):
    """ Approve order """

    def dispatch(self, request, *args, **kwargs):
        try:
            Order.objects.get(pk=kwargs['pk'])
        except:
            raise Order.DoesNotExist

        if request.user.is_superuser:
                return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


    def get(self, request, *args, **kwargs):
        order = Order.objects.get(pk=kwargs['pk'])
        order.approve()
        return redirect(reverse('order_list') + '?' + self.request.session.get('order_query_string', ''))


@method_decorator(is_staff, name='dispatch')
class InttaskDetail(DetailView):
    model = IntTask
    success_url = reverse_lazy('home_page')


@method_decorator(is_staff, name='dispatch')
class ReceiverList(ListView):
    """ ListView for Receivers.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Receiver
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 35

    def get_queryset(self):
        receivers = Receiver.objects.annotate(url=Concat(F('pk'), Value('/change/'), output_field=CharField())).\
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


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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
    paginate_by = 35

    def get_queryset(self):
        project_types = Project.objects.annotate(url=Concat(F('pk'), Value('/change/'), output_field=CharField()))\
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
        context['tasks_filtered'] = self.get_queryset().count()
        context['objects_count'] = Project.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ProjectFilterForm(self.request.POST)
        else:
            context['filter_form'] = forms.ProjectFilterForm(self.request.GET)

        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
class ProjectUpdate(UpdateView):
    model = Project
    form_class = forms.ProjectForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('project_type_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = context['project']
        context['header_main'] = 'Вид робіт'
        context['back_btn_url'] = reverse('project_type_delete', kwargs={'pk': name.pk})
        context['back_btn_text'] = 'Видалити'
        context['confirm_btn_text'] = 'Зберегти'
        context['formset_name'] = 'Підзадачі'

        if self.request.POST:
            context['formset'] = forms.SubTasksFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = forms.SubTasksFormSet(instance=self.object)

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        subtasks_formset = context['formset']
        if subtasks_formset.is_valid():
            with transaction.atomic():
                form.save()
                subtasks_formset.instance = self.object
                subtasks_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

@method_decorator(is_staff, name='dispatch')
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


@method_decorator(is_staff, name='dispatch')
class CustomerList(ListView):
    """ ListView for CustomerList.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Customer
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 35

    def get_queryset(self):
        debit_qry = Q(deal__act_status=Deal.Issued, deal__pay_status=Deal.NotPaid)
        customers = Customer.objects.annotate(
            url=Concat(F('pk'), Value('/change/'), output_field=CharField()),
            advance = Sum(Case(When(deal__pay_status=Deal.AdvancePaid, then=F('deal__value')),
                                    output_field=DecimalField(), default=0)),
            debit = Sum(Case(When(debit_qry, then=F('deal__value')),
                                  output_field=DecimalField(), default=0)),
            ).values_list('name', 'advance', 'debit', 'url')

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
                              ['debit', 'Дебітрська заборгованість', 0]]
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


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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


@method_decorator(is_staff, name='dispatch')
class CompanyList(ListView):
    """ ListView for CompanyList.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Company
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 35

    def get_queryset(self):
        companies = Company.objects.annotate(url=Concat(F('pk'), Value('/change/'), output_field=CharField()))\
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


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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


@method_decorator(is_staff, name='dispatch')
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
                                    .annotate(url=Concat(F('pk'), Value('/detail/'), output_field=CharField()))\
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


@method_decorator(is_staff, name='dispatch')
class EmployeeList(ListView):
    """ ListView for Employee.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Employee
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')

    def get_queryset(self):
        employees = Employee.objects.filter(user__is_active=True) \
                                    .order_by('name')\
                                    .annotate(url=Concat(F('pk'), Value('/change/'), output_field=CharField()))\
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
        context['objects_count'] = Employee.objects.filter(user__is_active=True).count()
        if self.request.POST:
            context['filter_form'] = forms.EmployeeFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.EmployeeFilterForm(self.request.GET)
        return context


@method_decorator(is_staff, name='dispatch')
class СolleagueDetail(DetailView):
    model = Employee
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
class EmployeeSelfUpdate(UpdateView):
    model = Employee
    form_class = forms.EmployeeSelfUpdateForm
    success_url = reverse_lazy('home_page')

    def get_object(self):
        return Employee.objects.get(user=get_current_user())


@method_decorator(is_staff, name='dispatch')
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


@method_decorator(is_staff, name='dispatch')
class ContractorList(ListView):
    """ ListView for Contractor.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Contractor
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 35

    def get_queryset(self):  # todo args url
        advance_qry = Q(order__pay_status=Order.AdvancePaid, order__task__exec_status__in=[Task.ToDo,Task.InProgress])
        credit_qry = Q(order__pay_status=Order.NotPaid, order__task__exec_status__in=[Task.Done,Task.Sent])
        contractors = Contractor.objects.annotate(
            url=Concat(F('pk'), Value('/change/'), output_field=CharField()),
            advance = Sum(Case(When(advance_qry, then=F('order__advance')),
                                    output_field=DecimalField(), default=0)),
            debit = Sum(Case(When(credit_qry, then=F('order__value')),
                                  output_field=DecimalField(), default=0)),
            ).\
            values_list('name', 'advance', 'debit', 'active', 'url')
        search_string = self.request.GET.get('filter')
        order = self.request.GET.get('o')
        if search_string:
            for word in search_string.split():
                contractors = contractors.filter(Q(name__icontains=word))
        if order:
            contractors = contractors.order_by(order)
        else:
            contractors = contractors.order_by('-active', 'name')
        return contractors

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['name', 'Назва', 1],
                              ['advance_calc', 'Авансові платежі', 0],
                              ['credit_calc', 'Кредиторська заборгованість', 0],
                              ['active', 'Активний', 0]]
        context['search'] = True
        context['filter'] = []
        if request.user.has_perm('planner.add_contractor'):
            context['add_url'] = reverse('contractor_add')
            context['add_help_text'] = 'Додати контрагента'
        context['header_main'] = 'Контрагенти'
        context['objects_count'] = Contractor.objects.all().count()
        if self.request.POST:
            context['filter_form'] = forms.ContractorFilterForm(
                self.request.POST)
        else:
            context['filter_form'] = forms.ContractorFilterForm(
                self.request.GET)

        return context


@method_decorator(is_staff, name='dispatch')
class ContractorCreate(CreateView):
    model = Contractor
    form_class = forms.ContractorForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('contractor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Додати контрагента'
        context['back_btn_url'] = reverse('contractor_list')
        context['back_btn_text'] = 'Відміна'
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
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
        context['confirm_btn_text'] = 'Зберегти'
        return context


@method_decorator(is_staff, name='dispatch')
class ContractorDelete(DeleteView):
    model = Contractor
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('contractor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contractor = context['contractor']
        context['go_back_url'] = reverse(
            'contractor_update', kwargs={'pk': contractor.pk})
        context['main_header'] = 'Видалити контрагента?'
        context['header'] = 'Видалення контрагента "' + \
            str(contractor) + \
            '" вимагатиме видалення наступних пов\'язаних об\'єктів:'
        if self.object.order_set.exists():
            context['objects'] = self.object.order_set.all()
        return context


@method_decorator(is_staff, name='dispatch')
class PlanList(ListView):
    """ ListView for Plans.
    Return in headers - 1.FieldName 2.VerboseName 3.NeedOrdering """
    model = Plan
    template_name = "planner/generic_list.html"
    success_url = reverse_lazy('home_page')
    paginate_by = 35

    def get_queryset(self):  # todo args url
        plans = Plan.objects.annotate(
            url=Concat(F('pk'), Value('/'), output_field=CharField()),
            total_duration=Coalesce(Sum('tasks__subtask__duration'), 0, output_field=DecimalField()),
            tasks_done_duration = Sum(Case(When(tasks__exec_status=Execution.Done, then=F('tasks__subtask__duration')),
                                  output_field=DecimalField(), default=0))) \
            .annotate(completion_percentage=F('tasks_done_duration')/F('total_duration')*100) \
            .values_list('owner__name', 'plan_start', 'plan_finish', 'completion_percentage', 'url')
        return plans

    def get_context_data(self, **kwargs):
        request = self.request
        context = super().get_context_data(**kwargs)
        context['headers'] = [['owner', 'ГІП', 0],
                              ['plan_start', 'Початкова дата', 0],
                              ['plan_finish', 'Кінцева дата', 0],
                              ['completion_percentage', 'Відсоток виконання', 0]]
        context['search'] = False
        context['filter'] = []
        if request.user.has_perm('planner.add_contractor'):
            context['add_url'] = reverse('plan_add')
            context['add_help_text'] = 'Створити план'
        context['header_main'] = 'Плани'
        context['objects_count'] = Plan.objects.all().count()

        return context


@method_decorator(is_staff, name='dispatch')
class PlanCreate(CreateView):
    model = Plan
    form_class = forms.PlanForm
    template_name = "planner/generic_form.html"
    success_url = reverse_lazy('plan_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_main'] = 'Створити план'
        context['back_btn_url'] = reverse('plan_list')
        context['back_btn_text'] = 'Відміна'
        context['confirm_btn_text'] = 'Створити'
        return context

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()

            query_dict = QueryDict('').copy()
            query_dict['owner'] = self.request.POST.get('owner')
            query_dict['actual_start'] = self.request.POST.get('plan_start')
            query_dict['actual_finish'] = self.request.POST.get('plan_finish')
            subtasks, _, _ = execuition_queryset_filter(self.request.user, query_dict)
            self.object.tasks.add(*subtasks)
            self.object.save()

            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


@method_decorator(is_staff, name='dispatch')
class PlanDetail(DetailView):
    model = Plan
    success_url = reverse_lazy('plan_list')


@method_decorator(is_staff, name='dispatch')
class PlanDelete(DeleteView):
    model = Plan
    template_name = "planner/generic_confirm_delete.html"
    success_url = reverse_lazy('plan_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = context['plan']
        context['go_back_url'] = reverse('plan_list')
        context['main_header'] = f'Видалити план {plan}?'
        return context


class ExecutionUpdateModal(BSModalUpdateView):
    model = Execution
    template_name = 'planner/execution_update.html'
    form_class = forms.ExecutionModelForm
    success_url = reverse_lazy('sprint_list')


class TaskUpdateModal(BSModalUpdateView):
    model = Task
    template_name = 'planner/task_update.html'
    form_class = forms.TaskModelForm
    success_url = reverse_lazy('task_list')
