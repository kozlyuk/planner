# -*- coding: utf-8 -*-

from datetime import date, timedelta
from decimal import Decimal
from django.contrib import admin
from django.db.models import Q, Sum
from django import forms
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from admin_totals.admin import ModelAdminTotals

from .models import ActOfAcceptance, Payment, Project, Employee, Customer, \
                    Receiver, Sending, Deal, Task, Execution, WorkType, \
                    IntTask, Contractor, Order, Company, Construction, SubTask


class SubTasksInline(admin.TabularInline):
    model = SubTask
    extra = 0
    show_change_link = True


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['project_type', 'customer', 'price_code',
                    'net_price', 'owner_bonus', 'executors_bonus', 'active']
    ordering = ['-price_code']
    list_filter = ['active', 'customer']
    fieldsets = [
        (None, {'fields': [('project_type', 'price_code'),
                           ('customer'),
                           ('price', 'net_price_rate'),
                           ('owner_bonus', 'executors_bonus'),
                           ('copies_count'),
                           ('description'),
                           ('active')
                           ]})
    ]
    inlines = [SubTasksInline]

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]


class EmployeeAdmin(admin.ModelAdmin):

    list_display = ['name', 'owner_count', 'task_count', 'inttask_count', 'card_number', 'salary']
    fieldsets = [
        (None, {'fields': [('user', 'name'),
                           ('position', 'head'),
                           ('phone', 'mobile_phone'),
                           ('vacation_count', 'vacation_date'),
                           ('salary', 'coefficient'),
                           ('birthday'),
                           ('avatar'),
                           ('card_number'),
                           ('comment'),
                           ]})
    ]

    def get_queryset(self, request):
        qs = super(EmployeeAdmin, self).get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name__in=['Бухгалтери', 'Секретарі']).exists():
            return qs.filter(user__is_active=True)
        return qs.filter(Q(user=request.user) | Q(head__user=request.user), user__is_active=True).distinct()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser or request.user.groups.filter(name__in=['Бухгалтери', 'Секретарі']).exists():
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'credit_calc',
                    'debit_calc', 'expect_calc', 'completed_calc']
    ordering = ['name']
    fieldsets = [
        (None, {'fields': [('name', 'full_name'),
                           'contact_person',
                           ('phone', 'email'),
                           ('user', 'debtor_term'),
                           ('signatory_person', 'signatory_position'),
                           ('regulations', 'city'),
                           ('requisites'),
                           ('legal'),
                           ('plan_reserve'),
                           ('deal_template'),
                           ('act_template'),
                           ('invoice_template'),
                           ('report_template'),
                           ('active'),
                           ]})
    ]

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]


class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'turnover_calc', 'costs_calc', 'bonuses_calc']
    ordering = ['name']
    fieldsets = [
        (None, {'fields': [('name', 'full_name'),
                           'chief',
                           ('taxation'),
                           ('signatory_person', 'signatory_position'),
                           ('regulations', 'city'),
                           ('requisites'),
                           ('legal'),
                           ('active'),
                           ]})
    ]

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]


class ContractorOrdersInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.is_valid():
                return
            pay_status = form.cleaned_data.get("pay_status")
            pay_date = form.cleaned_data.get("pay_date")
            value = form.cleaned_data.get("value")
            if pay_status and pay_status != Order.NotPaid:
                if not pay_date:
                    form.add_error('pay_date', 'Вкажіть будь ласка Дату оплати')
                if not value or value == 0:
                    form.add_error('value', 'Вкажіть будь ласка Вартість робіт')
            if pay_date and pay_status == Order.NotPaid:
                form.add_error('pay_status', 'Відмітьте Статус оплати або видаліть Дату оплати')


class OrderAdmin(ModelAdminTotals):
    list_display = ['contractor', 'task', 'subtask', 'value', 'pay_status',
                    'pay_date', 'get_exec_status', 'get_actual_finish']
    readonly_fields = ["contractor", "task", "subtask"]
    search_fields = ['contractor__name', 'subtask__name']
    list_filter = ['task__deal__company', 'pay_status', 'task__exec_status', ('contractor', RelatedDropdownFilter)]
    date_hierarchy = 'pay_date'
    ordering = ['-pay_date']
    list_totals = [('value', Sum)]

    def get_actual_finish(self, obj):
        return obj.task.actual_finish
    get_actual_finish.short_description = 'Фактичне закінчення'
    get_actual_finish.admin_order_field = 'task__actual_finish'


class ContractorOrdersInline(admin.TabularInline):
    model = Order
    formset = ContractorOrdersInlineFormSet
    fields = ['subtask', 'deal_number', 'value', 'advance', 'pay_status', 'pay_date', 'exec_status', 'actual_finish']
    readonly_fields = ['subtask', 'exec_status', 'actual_finish']
    ordering = ['pay_status', '-pay_date']
    extra = 0
    can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(pay_status=Order.PaidUp, pay_date__lte=date.today()-timedelta(days=365))

    def exec_status(self, obj):
        return obj.task.get_exec_status_display()
    exec_status.short_description = 'Статус проекту'

    def actual_finish(self, obj):
        return obj.task.actual_finish
    actual_finish.short_description = 'Дата виконання'


class ContractorAdmin(admin.ModelAdmin):
    list_display = ['name', 'advance_calc', 'credit_calc',
                    'expect_calc', 'completed_calc', 'active']
    search_fields = ['name', 'contact_person']
    list_filter = ['active']
    ordering = ['-active', 'name']
    fieldsets = [
        (None, {'fields': [('name', 'contact_person'),
                           ('phone', 'email'),
                           'requisites',
                           'active'
                           ]})
    ]
    inlines = [ContractorOrdersInline]


class ReceiverAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'contact_person', 'phone']
    ordering = ['name']
    fieldsets = [
        (None, {'fields': [('customer'),
                           ('name', 'address'),
                           ('contact_person', 'phone',),
                           ('comment')
                           ]})
    ]


class SendingAdmin(admin.ModelAdmin):
    list_display = ['receiver', 'task', 'receipt_date', 'copies_count']
    ordering = ['-receipt_date']
    list_filter = ['receiver']
    date_hierarchy = 'receipt_date'
    readonly_fields = ['task']
    fieldsets = [
        (None, {'fields': [('receiver'),
                           ('task'),
                           ('receipt_date', 'copies_count'),
                           ('comment')
                           ]})
    ]
    search_fields = ['task__object_code', 'task__object_address']

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if request.user.groups.filter(name='Секретарі').exists():
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.task.owner.user == request.user:
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None:
            if obj.task.owner.user == request.user:
                return True
        return False


class DealForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super(DealForm, self).clean()
        value = cleaned_data.get("value")
        pay_status = cleaned_data.get("pay_status")
        act_status = cleaned_data.get("act_status")
        pdf_copy = cleaned_data.get("pdf_copy")
        self.instance.__customer__ = cleaned_data.get("customer")
        self.instance.__expire_date__ = cleaned_data.get("expire_date")

        if pay_status == Deal.PaidUp:
            if not value or value == 0:
                raise forms.ValidationError("Вкажіть Вартість робіт")
        if act_status == Deal.PartlyIssued or act_status == Deal.Issued:
            if not value or value == 0:
                raise forms.ValidationError("Вкажіть Вартість робіт")
            if not pdf_copy:
                raise forms.ValidationError("Підвантажте будь ласка електронний примірник")


class TasksInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.is_valid():
                return
            project_type = form.cleaned_data.get("project_type")
            planned_finish = form.cleaned_data.get("planned_finish")
            if project_type and self.instance.__customer__:
                if self.instance.__customer__ != project_type.customer:
                    raise forms.ValidationError(
                        "Тип проекту не входить до можливих значень Замовника Договору")


class TasksInline(admin.TabularInline):

    model = Task
    formset = TasksInlineFormSet
    fields = ['object_code', 'object_address', 'project_type',
              'owner', 'planned_finish', 'exec_status', 'act_of_acceptance']
    readonly_fields = ['exec_status']
    extra = 0
    show_change_link = True
    can_delete = False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "owner":
            kwargs["queryset"] = Employee.objects.filter(
                user__groups__name__contains="ГІПи", user__is_active=True)
        if request._obj_ is not None and db_field.name == "project_type":
            kwargs["queryset"] = Project.objects.filter(
                customer=request._obj_.customer, active=True)
        if request._obj_ is not None and db_field.name == "act_of_acceptance":
            kwargs["queryset"] = ActOfAcceptance.objects.filter(deal=request._obj_)
        return super(TasksInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ActOfAcceptanceInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.is_valid():
                return
            pay_status = form.cleaned_data.get("pay_status")
            pay_date = form.cleaned_data.get("pay_date")
            value = form.cleaned_data.get("value")
            if pay_status and pay_status != Order.NotPaid:
                if not pay_date:
                    form.add_error('pay_date', 'Вкажіть будь ласка Дату оплати')
                if not value or value == 0:
                    form.add_error('value', 'Вкажіть будь ласка Вартість робіт')
            if pay_date and pay_status == Order.NotPaid:
                form.add_error('pay_status', 'Відмітьте Статус оплати або видаліть Дату оплати')


class ActOfAcceptanceInline(admin.TabularInline):

    model = ActOfAcceptance
    formset = ContractorOrdersInlineFormSet
    fields = ['number', 'date', 'value', 'pdf_copy']
    extra = 0
    show_change_link = True
    can_delete = False


class PaymentsInline(admin.TabularInline):

    model = Payment
    fields = ['date', 'value', 'act_of_acceptance']
    extra = 0
    show_change_link = True
    can_delete = False


class DealAdmin(admin.ModelAdmin):

    def warning_mark(self, obj):
        status = obj.warning
        if 'Протерміновано' in status:
            return format_html('<div style="color:red;">%s</div>' % status)
        elif 'Закінчується' in status:
            return format_html('<div style="color:orange;">%s</div>' % status)
        elif status == 'Очікує закриття акту' or 'Оплата' in status:
            return format_html('<div style="color:blue;">%s</div>' % status)
        elif 'Вартість' in status:
            return format_html('<div style="color:purple;">%s</div>' % status)
        return status

    warning_mark.allow_tags = True
    warning_mark.short_description = 'Попередження'

    form = DealForm
    list_display = ['number', 'customer', 'svalue', 'pay_status',
                    'act_status', 'exec_status', 'warning_mark']
    list_per_page = 50
    search_fields = ['number', 'value']
    ordering = ['-creation_date', 'customer', '-number']
    list_filter = [('customer', RelatedDropdownFilter),
                   ('company', RelatedDropdownFilter),
                   'pay_status', 'act_status']
    date_hierarchy = 'expire_date'
    readonly_fields = ['bonuses_calc',
                       'value_calc', 'costs_calc', 'pay_date_calc']
    fieldsets = [
        ('Інформація про договір', {'fields': [('number', 'date'),
                                               ('customer', 'company'),
                                               ('value', 'expire_date'),
                                               ('act_status', 'pay_status'),
                                               ('pdf_copy')]}),
        ('Додаткова інформація', {'fields': ['value_correction', 'value_calc', 'bonuses_calc',
                                             'costs_calc', 'pay_date_calc', 'manual_warning',
                                             'parent_deal_number', 'parent_deal_date'],
                                  'classes': ['collapse']})
    ]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(DealAdmin, self).get_form(request, obj, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            self.inlines = []
        else:
            self.inlines = [TasksInline, ActOfAcceptanceInline, PaymentsInline]
        return super(DealAdmin, self).get_inline_instances(request, obj)


class TaskForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super(TaskForm, self).clean()
        project_type = cleaned_data.get("project_type")
        deal = cleaned_data.get("deal")
        exec_status = cleaned_data.get("exec_status")
        pdf_copy = cleaned_data.get("pdf_copy")
        self.instance.__exec_status__ = exec_status
        self.instance.__project_type__ = project_type

        if project_type and deal:
            if deal.customer != project_type.customer:
                raise forms.ValidationError(
                    "Тип проекту не входить до можливих значень Замовника Договору")
        if exec_status in [Task.Done, Task.Sent] and not pdf_copy:
                raise forms.ValidationError(
                    "Підвантажте будь ласка електронний примірник")


class ExecutersInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(ExecutersInlineFormSet, self).clean()
        percent = 0
        outsourcing_part = 0
        self.instance.__outsourcing_part__ = outsourcing_part
        for form in self.forms:
            if not form.is_valid():
                return
            part = form.cleaned_data.get('part', 0)
            executor = form.cleaned_data.get('executor')
            percent += part
            if executor and executor.user.username.startswith('outsourcing'):
                outsourcing_part += part
            exec_status = form.cleaned_data.get('exec_status')
            actual_finish = form.cleaned_data.get('actual_finish')
            if actual_finish and exec_status != Execution.Done:
                raise ValidationError(
                    "Будь ласка відмітьте Статус виконання або видаліть Дату виконання")
            elif exec_status == Execution.Done and not actual_finish:
                raise ValidationError(
                    "Вкажіть будь ласка Дату виконання робіт")
        self.instance.__outsourcing_part__ = outsourcing_part
        if self.instance.__exec_status__ == Task.Done and percent < 100:
            raise ValidationError(
                _('Вкажіть 100%% часток виконавців. Зараз : %(percent).0f%%') % {'percent': percent})
        if self.instance.__project_type__:
            if self.instance.__project_type__.executors_bonus > 0:
                bonuses_max = 100 + 100 *\
                    self.instance.__project_type__.owner_bonus / \
                    self.instance.__project_type__.executors_bonus
            else:
                bonuses_max = 100
            if percent > bonuses_max:
                raise ValidationError(_('Сума часток виконавців не має перевищувати %(bonuses_max).0f%%. '
                                        'Зараз : %(percent).0f%%') % {'bonuses_max': bonuses_max, 'percent': percent})


class OrdersInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(OrdersInlineFormSet, self).clean()

        outsourcing = 0
        for form in self.forms:
            if form.is_valid():
                outsourcing += form.cleaned_data.get('value', 0)

        for form in self.forms:
            if not form.is_valid():
                return
            pay_status = form.cleaned_data.get("pay_status")
            pay_date = form.cleaned_data.get("pay_date")
            value = form.cleaned_data.get("value")
            if pay_status and pay_status != Order.NotPaid:
                if not pay_date:
                    raise forms.ValidationError(
                        "Вкажіть будь ласка Дату оплати")
                if not value or value == 0:
                    raise forms.ValidationError(
                        "Вкажіть будь ласка Вартість робіт")
            if pay_date and pay_status == Order.NotPaid:
                raise forms.ValidationError(
                    "Відмітьте Статус оплати або видаліть Дату оплати")

        if self.instance.__exec_status__ == Task.Done:
            if self.instance.__project_type__.net_price() > 0 and hasattr(self.instance, '__outsourcing_part__'):
                costs_part = outsourcing / self.instance.__project_type__.net_price() * 100 * Decimal(1.2)
                if self.instance.__outsourcing_part__ > 0 and costs_part == 0:
                    raise ValidationError(
                        'Добавте будь ласка витрати по аутсорсингу')
                if self.instance.__outsourcing_part__ < costs_part:
                    raise ValidationError(
                        'Відсоток витрат на аутсорсинг перевищує відсоток виконання робіт аутсорсингом')
            elif self.instance.__project_type__.net_price() == 0 and outsourcing > 0:
                raise ValidationError(
                    'У проекту вартість якого дорівнює нулю не може бути витрат')


class SendingsInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(SendingsInlineFormSet, self).clean()
        if self.instance.__exec_status__ == Task.Sent and not self.forms \
            and self.instance.project_type.copies_count > 0:
            raise forms.ValidationError(
                "Ви не можете закрити цей проект без відправки")


class ExecutersInline(admin.TabularInline):
    model = Execution
    formset = ExecutersInlineFormSet
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.owner.user == request.user and obj.is_active():
            return self.readonly_fields
        if request.user.groups.filter(name='Бухгалтери').exists() and obj.is_active():
            return self.readonly_fields
        fields = []
        for field in self.model._meta.fields:
            if not field.name == 'id':
                fields.append(field.name)
        self.can_delete = False
        self.max_num = 0
        return fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subtask":
            kwargs["queryset"] = SubTask.objects.filter(project_type=request._obj_.project_type)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SendingsInline(admin.TabularInline):
    model = Sending
    formset = SendingsInlineFormSet
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.owner.user == request.user and obj.is_active():
            return self.readonly_fields
        if request.user.groups.filter(name='Секретарі').exists():
            return self.readonly_fields
        fields = []
        for field in self.model._meta.fields:
            if not field.name == 'id':
                fields.append(field.name)
        self.can_delete = False
        self.max_num = 0
        return fields


class OrdersInline(admin.TabularInline):
    model = Order
    formset = OrdersInlineFormSet
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.owner.user == request.user and obj.is_active():
            return self.readonly_fields
        if request.user.groups.filter(name='Бухгалтери').exists() and obj.is_active():
            return self.readonly_fields
        fields = []
        for field in self.model._meta.fields:
            if not field.name == 'id':
                fields.append(field.name)
        self.can_delete = False
        self.max_num = 0
        return fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "contractor":
            kwargs["queryset"] = Contractor.objects.filter(active=True)
        return super(OrdersInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class TaskAdmin(admin.ModelAdmin):

    form = TaskForm

    def warning_mark(self, obj):
        status = obj.warning
        if 'Протерміновано' in status:
            return format_html('<div style="color:red;">%s</div>' % status)
        elif 'Завершується' in status:
            return format_html('<div style="color:orange;">%s</div>' % status)
        elif 'Завершити' in status:
            return format_html('<div style="color:blue;">%s</div>' % status)
        return status
    warning_mark.allow_tags = True
    warning_mark.short_description = 'Попередження'

    fieldsets = [
        ('Опис', {'fields': [('object_code', 'object_address', 'construction'),
                             ('project_type', 'deal')]}),
        ('Інформація про виконання', {'fields': [('exec_status', 'owner'),
                                                 ('tc_received', 'tc_upload'),
                                                 ('planned_start',
                                                  'planned_finish'),
                                                 ('actual_start', 'actual_finish'),
                                                 ('pdf_copy', )]}),
        ('Додаткова інформіція', {'fields': [
            'project_code', 'manual_warning',
            ('difficulty_owner', 'difficulty_executor')
            ],
            'classes': ['collapse']
            })
    ]
    list_display = ['object_code', 'object_address', 'project_type',
                    'deal', 'exec_status', 'owner', 'warning_mark']
    list_per_page = 50
    date_hierarchy = 'actual_finish'
    list_filter = ['exec_status',
                   ('owner', admin.RelatedOnlyFieldListFilter),
                   ('deal__customer', RelatedDropdownFilter)]
    search_fields = ['object_code', 'object_address',
                     'project_type__price_code', 'project_type__project_type', 'deal__number']
    ordering = ['-creation_date', '-deal', 'object_code']

    def get_form(self, request, obj=None, **kwargs):
        request._obj_ = obj
        form = super(TaskAdmin, self).get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            form.base_fields['owner'].queryset = Employee.objects.filter(
                user__groups__name__contains="ГІПи", user__is_active=True)
        elif obj is None or (obj.is_active() and obj.owner.user == request.user):
            form.base_fields['owner'].queryset = Employee.objects.filter(
                user=request.user)
        if obj is None or request.user.is_superuser or (obj.is_active() and obj.owner.user == request.user):
            if obj is None or obj.deal.act_status != Deal.Issued:
                form.base_fields['deal'].queryset = Deal.objects.exclude(
                    act_status=Deal.Issued).order_by('-creation_date')
            if obj is not None:
                form.base_fields['project_type'].queryset = Project.objects.filter(
                    customer=obj.deal.customer, active=True)
        return form

    def get_queryset(self, request):
        qs = super(TaskAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(Q(name='ГІПи') |
                                      Q(name='Бухгалтери') |
                                      Q(name='Секретарі')).exists():
            return qs
        return qs.filter(Q(owner__user=request.user) |
                         Q(executors__user=request.user) |
                         Q(executors__head__user=request.user)).distinct()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.owner.user == request.user and obj.is_active():
            return self.readonly_fields
        if request.user.groups.filter(name='Бухгалтери').exists():
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            self.inlines = [ExecutersInline]
        elif request.user.groups.filter(Q(name='ГІПи') | Q(name='Бухгалтери')).exists():
            self.inlines = [ExecutersInline, OrdersInline, SendingsInline]
        else:
            self.inlines = [ExecutersInline, SendingsInline]
        return super(TaskAdmin, self).get_inline_instances(request, obj)


class IntTaskAdmin(admin.ModelAdmin):

    list_display = ['task_name', 'exec_status',
                    'executor', 'actual_finish']
    fieldsets = [
        (None, {'fields': ['task_name',
                           ('exec_status', 'executor'),
                           ('planned_start', 'planned_finish'),
                           ('actual_start', 'actual_finish'),
                           'bonus',
                           'comment'
                           ]})
    ]
    list_per_page = 50
    date_hierarchy = 'actual_finish'
    list_filter = ['exec_status',
                   ('executor', admin.RelatedOnlyFieldListFilter)]
    search_fields = ['task_name']

    def get_queryset(self, request):
        qs = super(IntTaskAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(executor__user=request.user) |
                         Q(executor__head__user=request.user)).distinct()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return self.readonly_fields
        if obj.executor.user == request.user:
            return self.readonly_fields
        return [f.name for f in self.model._meta.fields]


class SubTaskAdmin(admin.ModelAdmin):

    list_display = ['name', 'project_type', 'part', 'base', 'add_to_schedule', 'check_required']
    list_per_page = 100
    list_filter = ['project_type__active',
                   'base',
                   'add_to_schedule',
                   'check_required',
                   ('project_type__customer', RelatedDropdownFilter),
                   ('project_type', RelatedDropdownFilter)]
    search_fields = ['name', 'project_type__project_type', 'project_type__price_code']



admin.AdminSite.site_header = 'Адміністратор проектів Ітел-Сервіс'
admin.AdminSite.site_title = 'Itel-Service ERP'
admin.site.disable_action('delete_selected')

admin.site.register(Project, ProjectAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Contractor, ContractorAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Receiver, ReceiverAdmin)
admin.site.register(Sending, SendingAdmin)
admin.site.register(Deal, DealAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(IntTask, IntTaskAdmin)
admin.site.register(Construction)
admin.site.register(WorkType)
admin.site.register(SubTask, SubTaskAdmin)
