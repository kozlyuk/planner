from datetime import date, timedelta
from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AdminDateWidget
from .DateTimeWidgets import SplitDateTimeWidget
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django_select2.forms import Select2Widget, Select2MultipleWidget
from crum import get_current_user

from .models import ActOfAcceptance, Construction, Payment, SubTask, Task, Customer, Execution, Order, Sending, \
                    Deal, Employee, Project, Company, Receiver, Contractor
from html_templates.models import HTMLTemplate
from .formatChecker import NotClearableFileInput, AvatarInput
from .btnWidget import BtnWidget


class UserLoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'password')
        widgets = {'password': forms.PasswordInput}

    def is_valid(self):
        username_ = self.data["username"]
        try:
            User.objects.get(username=username_)
            self.errors.clear()
            self.cleaned_data["username"] = username_
            return True
        except User.DoesNotExist:
            return False


class EmployeeForm(forms.ModelForm):
    """ EmployeeForm - form for employees creating or updating """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vacation_date'].widget = forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'})
        self.fields['birthday'].widget = forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'})
        groups = [(group.id, group.name) for group in Group.objects.all()]
        self.fields['groups'].choices = groups

    username = forms.CharField(label='Логін', max_length=255, required=True)
    password = forms.CharField(
        label='Пароль', max_length=255, required=True, widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Підтвердити пароль', max_length=255, required=True,
                                       widget=forms.PasswordInput)
    email = forms.EmailField(label='Електронна пошта',
                             max_length=255, required=True)
    groups = forms.ChoiceField(label='Група', required=False)

    class Meta:
        model = Employee
        fields = ['name', 'position', 'head', 'phone', 'mobile_phone', 'avatar',
                  'birthday', 'salary', 'vacation_count', 'vacation_date']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        username = cleaned_data.get('username')
        pib_name = self.cleaned_data.get('name').split()
        email = cleaned_data.get('email')

        if password != password_confirm:
            self.add_error('password_confirm', 'Password does not match')
        if User.objects.filter(username=username).exists():
            self.add_error('username', 'User with such username already exist')
        if User.objects.filter(email=email).exists():
            self.add_error('email', 'User with such email already exist')
        if len(pib_name) < 2:
            self.add_error('name', 'Please write full name of employee')

    def save(self, commit=True):
        instance = super().save(commit=False)

        username = self.cleaned_data.get('username')
        pib_name = self.cleaned_data.get('name').split()
        password = self.cleaned_data.get('password')
        email = self.cleaned_data.get('email')
        groups = self.cleaned_data.get('groups')

        user = User(username=username, email=email, is_staff=True,
                    first_name=pib_name[0], last_name=pib_name[1])
        user.set_password(password)

        if commit:
            user.save()
            for group_pk in groups:
                group = Group.objects.get(pk=group_pk)
                group.user_set.add(user)
            instance.user = user
            instance.save()
        return instance


class DealFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DealFilterForm, self).__init__(*args, **kwargs)
        customer = list(Customer.objects.all().values_list('pk', 'name'))
        company = list(Company.objects.all().values_list('pk', 'name'))
        act_status = list(Deal.ACT_STATUS_CHOICES)
        pay_status = list(Deal.PAYMENT_STATUS_CHOICES)
        exec_status = list(Deal.EXEC_STATUS_CHOICES)
        specific_status = list(Deal.SPECIFIC_STATUS_CHOICES)

        self.fields['customer'].choices = customer
        self.fields['company'].choices = company
        self.fields['act_status'].choices = act_status
        self.fields['pay_status'].choices = pay_status
        self.fields['exec_status'].choices = exec_status
        self.fields['specific_status'].choices = specific_status

    customer = forms.MultipleChoiceField(label='Замовник', required=False,
        widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    company = forms.MultipleChoiceField(label='Компанія', required=False,
        widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    act_status = forms.MultipleChoiceField(label='Акт виконаних робіт', required=False,
        widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    pay_status = forms.MultipleChoiceField(label='Статус оплати', required=False,
        widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    exec_status = forms.MultipleChoiceField(label='Статус виконання', required=False,
        widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    specific_status = forms.ChoiceField(label='Спеціальний статус', required=False,
        widget=Select2Widget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    filter = forms.CharField(label='Слово пошуку', max_length=255, required=False,
        widget=forms.TextInput(attrs={"style": 'width: 100%', "class": 'select2-container--bootstrap select2-selection'}))


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ['number', 'date', 'customer', 'company', 'value', 'expire_date',
                  'pdf_copy', 'value_correction', 'comment', 'manual_warning',
                  'parent_deal_number', 'parent_deal_date']
        widgets = {
            'date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'customer': Select2Widget,
            'company': Select2Widget,
            'expire_date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'parent_deal_date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'pdf_copy': NotClearableFileInput,
        }

    def __init__(self, *args, **kwargs):
        super(DealForm, self).__init__(*args, **kwargs)
        self.fields['number'].widget.attrs.update({'style': 'width:100%'})
        self.fields['comment'].widget.attrs.update({'style': 'width:100%; height:44px;'})

    def clean(self):
        cleaned_data = super(DealForm, self).clean()
        self.data.__customer__ = cleaned_data.get("customer")
        self.data.__expire_date__ = cleaned_data.get("expire_date")
        self.data.__value__ = cleaned_data.get("value")

        return cleaned_data


class TasksInlineForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['object_code', 'object_address', 'project_type',
                  'owner', 'planned_finish', 'exec_status', 'act_of_acceptance']
        widgets = {
            'object_code': BtnWidget(),
            'project_type': Select2Widget(),
            'planned_finish': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'DELETE': forms.HiddenInput(),
        }

    def __init__(self, *args, method=None, owners=None, project_types=None, acts=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['object_code'].widget.attrs.update({'task_id': self.instance.id})
        if method == 'GET':
            self.fields['owner'].queryset = owners
            self.fields['project_type'].queryset = project_types
            self.fields['act_of_acceptance'].queryset = acts

    def clean(self):
        super().clean()
        project_type = self.cleaned_data.get("project_type")
        planned_finish = self.cleaned_data.get("planned_finish")
        if project_type and self.data.__customer__:
            if self.data.__customer__ != project_type.customer:
                self.add_error(
                    'project_type', "Тип проекту не входить до можливих значень Замовника Договору")
        if planned_finish and self.data.__expire_date__:
            if planned_finish > self.data.__expire_date__:
                self.add_error(
                    'planned_finish', "Планова дата закінчення повинна бути меншою дати закінчення договору")


TasksFormSet = inlineformset_factory(Deal, Task, form=TasksInlineForm, extra=0)


class ActOfAcceptanceInlineForm(forms.ModelForm):
    class Meta:
        model = ActOfAcceptance
        fields = ['number', 'date', 'value', 'pdf_copy']
        widgets = {
            'date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'DELETE': forms.HiddenInput(),
            'pdf_copy': NotClearableFileInput,
        }


class ActOfAcceptanceInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""

    def clean(self):
        super().clean()
        value_sum = 0
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                value_sum += form.cleaned_data.get('value', 0)
        if self.instance.pk and value_sum > self.data.__value__:
            raise ValidationError(f'Сума актів не повинна перевищувати суму договору. Наразі: {value_sum}')


ActOfAcceptanceFormSet = inlineformset_factory(Deal, ActOfAcceptance, form=ActOfAcceptanceInlineForm,
                                               extra=0, formset=ActOfAcceptanceInlineFormset)


class PaymentInlineForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['date', 'value', 'act_of_acceptance']
        widgets = {
            'date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'DELETE': forms.HiddenInput(),
        }

    def __init__(self, *args, acts=None, **kwargs):
        super().__init__(*args, **kwargs)
        if acts:
            self.fields['act_of_acceptance'].queryset = acts


class PaymentInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""

    def clean(self):
        super().clean()
        value_sum = 0
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                value_sum += form.cleaned_data.get('value', 0)
        if self.instance.pk and value_sum > self.data.__value__:
            raise ValidationError(f'Сума оплат не повинна перевищувати суму договору. Наразі: {value_sum}')


PaymentFormSet = inlineformset_factory(Deal, Payment, form=PaymentInlineForm, extra=0, formset=PaymentInlineFormset)


class TaskFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exec_status = list(Task.EXEC_STATUS_CHOICES)
        owners = list(Employee.objects.filter(user__is_active=True, user__groups__name='ГІПи')
                                      .values_list('pk', 'name'))
        customers = list(Customer.objects.all().values_list('pk', 'name'))
        constructions = list(Construction.objects.all().values_list('pk', 'name'))

        self.fields['exec_status'].choices = exec_status
        self.fields['owner'].choices = owners
        self.fields['customer'].choices = customers
        self.fields['construction'].choices = constructions

    exec_status = forms.MultipleChoiceField(
        label='Статус', required=False, widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    owner = forms.MultipleChoiceField(label='Керівник проекту', required=False,
                              widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    customer = forms.MultipleChoiceField(label='Замовник', required=False, widget=Select2MultipleWidget(
        attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    construction = forms.MultipleChoiceField(
        label='Тип конструкції', required=False, widget=Select2MultipleWidget(attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False, widget=forms.TextInput(
                                 attrs={"style": 'width: 100%', "class": 'select2-container--bootstrap select2-selection'}))


class SprintFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = get_current_user()
        exec_status = list(Execution.EXEC_STATUS_CHOICES)
        companies = list(Company.objects.all().values_list('pk', 'name'))

        # what executors is available in filter
        if user.is_superuser or user.groups.filter(name='Замовники').exists():
            executors = list(Employee.objects.filter(user__is_active=True).values_list('pk', 'name'))
        elif user.groups.filter(name='ГІПи').exists():
            executors = list(Employee.objects.filter(Q(head=user.employee) | Q(user=user), user__is_active=True)
                             .values_list('pk', 'name'))
        elif user.groups.filter(name='Проектувальники').exists():
            executors = list(Employee.objects.filter(user=user).values_list('pk', 'name'))

        self.fields['exec_status'].choices = exec_status
        self.fields['executor'].choices = executors
        self.fields['company'].choices = companies

    exec_status = forms.MultipleChoiceField(label='Статус', required=False,
                                            widget=Select2MultipleWidget(
                                                attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    executor = forms.MultipleChoiceField(label='Виконавець', required=False,
                                         widget=Select2MultipleWidget(
                                             attrs={"onChange": 'submit()', "style": 'width: 100%'}))
    company = forms.MultipleChoiceField(label='Компанія', required=False,
                                        widget=Select2MultipleWidget(
                                            attrs={"onChange": 'submit()', "style": 'width: 100%'}))

    start_date_value = date.today() - timedelta(days=date.today().weekday())
    finish_date_value = start_date_value + timedelta(days=14)
    start_date = forms.DateField(label='Дата початку',
                                 widget=forms.DateInput(format=('%d.%m.%Y'),
                                 attrs={'type': 'date', "value": start_date_value.strftime('%Y-%m-%d'), "style": 'width: 100%'}))
    finish_date = forms.DateField(label='Дата завершення',
                                 widget=forms.DateInput(format=('%d.%m.%Y'),
                                 attrs={'type': 'date', "value": finish_date_value.strftime('%Y-%m-%d'), "style": 'width: 100%'}))
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False, widget=forms.TextInput(
                                 attrs={"style": 'width: 100%', "class": 'select2-container--bootstrap select2-selection'}))


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['object_code', 'object_address', 'tc_received',
                  'project_type', 'deal', 'tc_upload',
                  'owner', 'exec_status', 'pdf_copy',
                  'planned_start', 'planned_finish', 'actual_finish',
                  'project_code', 'manual_warning', 'comment',
                  'difficulty_owner', 'difficulty_executor',
                  'construction'
                  ]
        widgets = {
            'project_type': Select2Widget,
            'deal': Select2Widget,
            'planned_start': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'planned_finish': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'actual_finish': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'tc_received': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'tc_upload': NotClearableFileInput,
            'pdf_copy': NotClearableFileInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if get_current_user().is_superuser:
            self.fields['owner'].queryset = Employee.objects.filter(user__groups__name__contains="ГІПи",
                                                                    user__is_active=True)
        elif self.instance.pk is None or self.instance.owner.user == get_current_user():
            self.fields['owner'].queryset = Employee.objects.filter(user=get_current_user())

        if self.instance.pk is None or self.instance.deal.act_status == Deal.NotIssued:
            self.fields['deal'].queryset = Deal.objects.filter(act_status=Deal.NotIssued).select_related('customer')
        else:
            self.fields['deal'].queryset = Deal.objects.filter(pk=self.instance.deal.pk).select_related('customer')
            self.fields['deal'].widget.attrs['disabled'] = True
            self.fields['deal'].required = False

        if self.instance.pk is None or self.instance.project_type.active:
            self.fields['project_type'].queryset = Project.objects.filter(active=True)
        else:
            self.fields['project_type'].queryset = Project.objects.filter(pk=self.instance.project_type.pk)
            self.fields['project_type'].widget.attrs['disabled'] = True
            self.fields['project_type'].required = False

    def clean_deal(self):
        if self.cleaned_data['deal']:
            return self.cleaned_data['deal']
        else:
            return self.instance.deal

    def clean_project_type(self):
        if self.cleaned_data['project_type']:
            return self.cleaned_data['project_type']
        else:
            return self.instance.project_type

    def clean(self):
        cleaned_data = super(TaskForm, self).clean()
        project_type = cleaned_data.get("project_type")
        deal = cleaned_data.get("deal")
        exec_status = cleaned_data.get("exec_status")
        planned_finish = cleaned_data.get("planned_finish")
        pdf_copy = cleaned_data.get("pdf_copy")
        project_code = cleaned_data.get("project_code")
        self.instance.__project_type__ = project_type
        self.instance.__exec_status__ = exec_status

        if not get_current_user().is_superuser and (not deal or deal.act_status == Deal.Issued):
            raise ValidationError("Договір закрито, зверніться до керівника")
        if not project_type or project_type.active is False:
            raise ValidationError("Даний Тип проекту не активний")
        if project_type and deal:
            if deal.customer != project_type.customer:
                self.add_error('project_type', "Тип проекту не відповідає Замовнику Договору")
        if exec_status in [Task.Done, Task.Sent] and not pdf_copy:
            self.add_error('pdf_copy', "Підвантажте будь ласка електронний примірник")
        if planned_finish and planned_finish > deal.expire_date:
            self.add_error('planned_finish', "Планова дата закінчення повинна бути меншою дати закінчення договору")
        if project_code and Task.objects.filter(project_code=project_code).exclude(pk=self.instance.pk).exists():
            self.add_error('project_code', "Проект з таким шифром вже існує")
        return cleaned_data


class ExecutorInlineForm(forms.ModelForm):
    class Meta:
        model = Execution
        fields = ['executor', 'subtask', 'part', 'exec_status',
                  'finish_date', 'planned_start', 'planned_finish', 'warning']
        widgets = {
            'executor': Select2Widget(),
            'subtask': Select2Widget(),
            'planned_start': SplitDateTimeWidget(),
            'planned_finish': SplitDateTimeWidget(),
            'finish_date': SplitDateTimeWidget(),
            'DELETION_FIELD_NAME': forms.HiddenInput()
        }

    def __init__(self, *args, method=None, employees=None, subtasks=None, **kwargs):
        super().__init__(*args, **kwargs)

        if method == 'GET':
            if not (self.instance.executor and self.instance.executor.user.is_active == False):
                self.fields['executor'].queryset = employees
            self.fields['subtask'].queryset = subtasks

    def clean(self):
        super().clean()
        if self.instance.pk and self.changed_data:
            if self.instance.is_active() == False and not get_current_user().is_superuser:
                self.add_error('executor', "Ця підзадача виконана більше 10 днів тому")


class ExecutorsInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""

    def clean(self):
        """forces each clean() method on the ChildCounts to be called"""
        super().clean()
        # Calculating outsourcing part
        percent = 0
        outsourcing_part = 0
        self.instance.__outsourcing_part__ = 0
        for form in self.forms:
            part = form.cleaned_data.get('part', 0)
            executor = form.cleaned_data.get('executor')
            if not form.cleaned_data.get('DELETE', False):
                percent += part
                if executor and executor.user.username.startswith('outsourcing'):
                    outsourcing_part += part
            if self.instance.__exec_status__ in [Task.Done, Task.Sent] and not executor:
                raise ValidationError('Зазначте усіх виконавців')
        self.instance.__outsourcing_part__ = outsourcing_part
        # Check if sum of executions parts more than 100% and less then 150%
        if self.instance.pk:
            if self.instance.__exec_status__ in [Task.Done, Task.Sent] and percent < 100:
                raise ValidationError(
                    ('Вкажіть 100%% часток виконавців. Зараз : %(percent).0f%%') % {'percent': percent})
            if self.instance.__project_type__.executors_bonus > 0:
                bonuses_max = 100 + 100 * self.instance.__project_type__.owner_bonus /\
                    self.instance.__project_type__.executors_bonus
            else:
                bonuses_max = 100
            if percent > bonuses_max:
                raise ValidationError(('Сума часток виконавців не має перевищувати %(bonuses_max).0f%%. '
                                       'Зараз : %(percent).0f%%') % {'bonuses_max': bonuses_max, 'percent': percent})


ExecutorsFormSet = inlineformset_factory(
    Task, Execution, form=ExecutorInlineForm, extra=0, formset=ExecutorsInlineFormset)


class OrderInlineForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['contractor', 'subtask', 'deal_number', 'value',
                  'advance', 'pay_status', 'pay_date']
        widgets = {
            'contractor': Select2Widget(),
            'subtask': Select2Widget(),
            'pay_date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'DELETION_FIELD_NAME': forms.HiddenInput()
        }

    def __init__(self, *args, method=None, contractors=None, subtasks=None, **kwargs):
        super().__init__(*args, **kwargs)

        if method == 'GET':
            if not (self.instance.pk and self.instance.contractor.active == False):
                self.fields['contractor'].queryset = contractors
            self.fields['subtask'].queryset = subtasks

    def clean(self):
        super(OrderInlineForm, self).clean()
        pay_status = self.cleaned_data.get("pay_status")
        pay_date = self.cleaned_data.get("pay_date")
        value = self.cleaned_data.get("value")
        if pay_status and pay_status != Order.NotPaid:
            if not pay_date:
                self.add_error('pay_date', "Вкажіть будь ласка Дату оплати")
            if not value or value == 0:
                self.add_error('value', "Вкажіть будь ласка Вартість робіт")
        if pay_date and pay_status == Order.NotPaid:
            self.add_error('pay_status', "Відмітьте Статус оплати або видаліть Дату оплати")


class CostsInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""

    def clean(self):
        """forces each clean() method on the ChildCounts to be called"""
        super(CostsInlineFormset, self).clean()
        outsourcing = 0
        for form in self.forms:
            if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                outsourcing += form.cleaned_data.get('value', 0)
        if self.instance.pk:
            if self.instance.__exec_status__ in [Task.Done, Task.Sent]:
                if self.instance.__project_type__.net_price() > 0 and hasattr(self.instance, '__outsourcing_part__'):
                    costs_part = outsourcing / self.instance.__project_type__.net_price() * 100 * Decimal(1.2)
                    if self.instance.__outsourcing_part__ > 0 and costs_part == 0:
                        raise ValidationError("Добавте будь ласка витрати по аутсорсингу")
                    if self.instance.__outsourcing_part__ < costs_part and not get_current_user().is_superuser:
                        raise ValidationError("Відсоток витрат на аутсорсинг перевищує відсоток виконання робіт аутсорсингом")
                elif self.instance.__project_type__.net_price() == 0 and outsourcing > 0:
                    raise ValidationError("У проекту вартість якого дорівнює нулю не може бути витрат")


CostsFormSet = inlineformset_factory(Task, Order, form=OrderInlineForm, extra=0, formset=CostsInlineFormset)


class SendingInlineForm(forms.ModelForm):
    class Meta:
        model = Sending
        fields = ['receiver', 'receipt_date', 'copies_count', 'register_num']
        widgets = {
            'receiver': Select2Widget(),
            'receipt_date': forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
            'DELETION_FIELD_NAME': forms.HiddenInput()
        }


class SendingInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""

    def clean(self):
        """forces each clean() method on the ChildCounts to be called"""
        super(SendingInlineFormset, self).clean()
        if self.instance.pk:
            if self.instance.__exec_status__ == Task.Sent and self.instance.__project_type__.copies_count > 0:
                sending = 0
                for form in self.forms:
                    if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                        sending += form.cleaned_data.get('copies_count', 0)
                if sending == 0:
                    raise ValidationError(
                        "Ви не можете закрити цей проект без відправки")


SendingFormSet = inlineformset_factory(
    Task, Sending, form=SendingInlineForm, extra=0, formset=SendingInlineFormset)


class TaskExchangeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.tasks_ids = kwargs.pop('tasks_ids')
        super().__init__(*args, **kwargs)
        deal = [(deal.id, deal.number)
                for deal in Deal.objects.filter(act_status=Deal.NotIssued)]
        self.fields['deal'].choices = deal

    deal = forms.ChoiceField(label='Оберіть договір', widget=Select2Widget())

    def clean(self):
        super().clean()
        deal_id = self.cleaned_data.get("deal")
        tasks = Task.objects.filter(id__in=self.tasks_ids)
        if not self.tasks_ids:
            raise ValidationError("Ви не обрали жодного проекту")
        if deal_id:
            deal = Deal.objects.get(pk=deal_id)
            for task in tasks:
                if deal.customer != task.project_type.customer:
                    self.add_error(
                        'deal', "{} - тип проекту не відповідає Замовнику Договору".format(task))
                if task.deal.act_status != Deal.NotIssued:
                    self.add_error(
                        'deal', "{} - договір закрито, зверніться до керівника".format(task))


# class TaskRegistryForm(forms.Form):
#     def __init__(self, *args, **kwargs):
#         self.tasks_ids = kwargs.pop('tasks_ids')
#         super().__init__(*args, **kwargs)
#         deal = [(deal.id, deal.number) for deal in .objects.filter(act_status=Deal.NotIssued)]
#         self.fields['deal'].choices = deal
#
#     receiver = forms.ChoiceField(label='Оберіть отримувача', widget=Select2Widget())
#     receipt_date = forms.DateField(label='Дата реєстру', widget=AdminDateWidget())
#     copies_count = forms.CharField(label='Кількість примірників')
#     register_num = forms.CharField(label='Номер реєстру')


class EmployeeSelfUpdateForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['mobile_phone', 'avatar']
        widgets = {
            'avatar': AvatarInput,
        }


class ReceiverFilterForm(forms.Form):
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class ReceiverForm(forms.ModelForm):
    class Meta:
        model = Receiver
        fields = ['customer', 'name', 'address', 'contact_person', 'phone']


class ProjectFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        customers = list(Customer.objects.all().values_list('pk', 'name'))
        customers.insert(0, (0, "Всі"))
        self.fields['customer'].choices = customers

    customer = forms.ChoiceField(label='Замовник', required=False, widget=forms.Select(
        attrs={"onChange": 'submit()'}))
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['project_type', 'price_code', 'customer', 'price', 'net_price_rate',
                  'owner_bonus', 'executors_bonus', 'copies_count', 'description',
                  'need_project_code', 'active']

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs.update({'style': 'height:100px;'})
        self.fields['active'].widget.attrs.update({'style': 'height:15px;'})
        self.fields['need_project_code'].widget.attrs.update({'style': 'height:15px;'})


class CustomerFilterForm(forms.Form):
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'full_name', 'contact_person', 'phone', 'email',
                  'debtor_term', 'user',
                  'city', 'legal', 'regulations',
                  'signatory_person', 'signatory_position', 'requisites',
                  'deal_template', 'act_template', 'invoice_template', 'report_template', 'active',
                  ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deal_template'].queryset = HTMLTemplate.objects.filter(document_type=HTMLTemplate.Deal)
        self.fields['act_template'].queryset = HTMLTemplate.objects.filter(document_type=HTMLTemplate.Act)
        self.fields['invoice_template'].queryset = HTMLTemplate.objects.filter(document_type=HTMLTemplate.Invoice)
        self.fields['report_template'].queryset = HTMLTemplate.objects.filter(document_type=HTMLTemplate.Report)
        self.fields['active'].widget.attrs.update({'style': 'height:15px;'})


class CompanyFilterForm(forms.Form):
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'full_name', 'chief', 'taxation',
                  'city', 'legal', 'regulations',
                  'signatory_person', 'signatory_position',
                  'requisites', 'active',
                  ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['active'].widget.attrs.update({'style': 'height:15px;'})


class ContractorFilterForm(forms.Form):
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['name', 'contact_person', 'phone',
                  'email', 'requisites', 'active']

    def __init__(self, *args, **kwargs):
        super(ContractorForm, self).__init__(*args, **kwargs)
        self.fields['requisites'].widget.attrs.update(
            {'style': 'height:50px;'})
        self.fields['active'].widget.attrs.update({'style': 'height:15px;'})


class EmployeeFilterForm(forms.Form):
    filter = forms.CharField(label='Слово пошуку',
                             max_length=255, required=False)


class SubTasksInlineForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ['name', 'part', 'duration', 'base', 'add_to_schedule']
        widgets = {
            'part': forms.TextInput(attrs={'style' : 'height:34px'}),
            'base': forms.CheckboxInput(attrs={'style' : 'height:15px'}),
            'add_to_schedule': forms.CheckboxInput(attrs={'style' : 'height:15px'}),
        }


SubTasksFormSet = inlineformset_factory(Project, SubTask, form=SubTasksInlineForm,
                                        extra=0, can_delete=False)
