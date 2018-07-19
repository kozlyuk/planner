# -*- encoding: utf-8 -*-
from django import forms
from .models import User, Task, Customer, Execution, Order, Sending, Deal, Employee, Project
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django_select2.forms import Select2Widget
from django.contrib.admin.widgets import AdminDateWidget
from crum import get_current_user


class UserLoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'password')
        widgets = {'password': forms.PasswordInput}

    def is_valid(self):
        username_ = self.data["username"]
        try:
            User._default_manager.get(username=username_)
            self.errors.clear()
            self.cleaned_data["username"] = username_
            return True
        except:
            return False


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['object_code', 'object_address', 'project_type', 'deal', 'exec_status', 'owner',
                  'planned_start', 'planned_finish', 'actual_start', 'actual_finish',
                  'tc_received', 'tc_upload', 'pdf_copy', 'project_code', 'comment']
        widgets = {
            'project_type': Select2Widget,
            'deal': Select2Widget,
            'planned_start': AdminDateWidget,
            'planned_finish': AdminDateWidget,
            'actual_start': AdminDateWidget,
            'actual_finish': AdminDateWidget,
            'tc_received': AdminDateWidget,
        }

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['object_address'].widget.attrs.update({'style': 'width:100%;'})
        self.fields['comment'].widget.attrs.update({'style': 'width:100%; height:63px;'})

        if get_current_user().is_superuser:
            self.fields['owner'].queryset = Employee.objects.filter(user__groups__name__contains="ГІПи",
                                                                    user__is_active=True)
        elif self.instance.pk is None or self.instance.owner.user == get_current_user():
            self.fields['owner'].queryset = Employee.objects.filter(user=get_current_user())

        if self.instance.pk is None or self.instance.deal.act_status != Deal.Issued:
            self.fields['deal'].queryset = Deal.objects.exclude(act_status=Deal.Issued)
        else:
            self.fields['deal'].widget.attrs['disabled'] = True

        if self.instance.pk is None:
            self.fields['project_type'].queryset = Project.objects.filter(active=True)
        else:
            self.fields['project_type'].queryset = Project.objects.filter(customer=self.instance.deal.customer,
                                                                          active=True)

    def clean(self):
        cleaned_data = super(TaskForm, self).clean()
        project_type = cleaned_data.get("project_type")
        deal = cleaned_data.get("deal")
        exec_status = cleaned_data.get("exec_status")
        actual_finish = cleaned_data.get("actual_finish")
        planned_finish = cleaned_data.get("planned_finish")
        pdf_copy = cleaned_data.get("pdf_copy")

        if project_type and deal:
            if deal.customer != project_type.customer:
                self.add_error('project_type', "Тип проекту не входить до можливих значень Замовника Договору")
        if exec_status in [Task.Done, Task.Sent]:
            if not actual_finish:
                self.add_error('actual_finish', "Вкажіть будь ласка Фактичне закінчення робіт")
            elif not pdf_copy:
                self.add_error('pdf_copy', "Підвантажте будь ласка електронний примірник")
            elif deal.act_status == Deal.Issued:
                self.add_error(None, "Договір закрито, зверніться до керівника")
        if actual_finish and exec_status not in [Task.Done, Task.Sent]:
            self.add_error('exec_status', "Будь ласка відмітьте Статус виконання або видаліть Дату виконання")
        if planned_finish and planned_finish > deal.expire_date:
            self.add_error('planned_finish', "Планова дата закінчення повинна бути меншою дати закінчення договору")
        return cleaned_data


class ExecutorInlineForm(forms.ModelForm):
    class Meta:
        model = Execution
        fields = ['executor', 'part_name', 'part', 'exec_status', 'finish_date']
        widgets = {
            'executor': Select2Widget(),
            'finish_date': AdminDateWidget(),
            'DELETION_FIELD_NAME': forms.HiddenInput()
        }

    def clean(self):
        super(ExecutorsInlineForm, self).clean()
        exec_status = self.cleaned_data.get('exec_status')
        finish_date = self.cleaned_data.get('finish_date')
        if finish_date and exec_status != Execution.Done:
            self.add_error('exec_status', "Будь ласка відмітьте Статус виконання або видаліть Дату виконання")
        elif exec_status == Execution.Done and not finish_date:
            self.add_error('finish_date', "Вкажіть будь ласка Дату виконання робіт")


class ExecutorsInlineFormset(BaseInlineFormSet):
    """used to pass in the constructor of inlineformset_factory"""
    def clean(self):
        """forces each clean() method on the ChildCounts to be called"""
        super(ExecutorsInlineFormset, self).clean()
        percent = 0
        outsourcing_part = 0
        self.instance.__outsourcing_part__ = 0
        for form in self.forms:
            part = form.cleaned_data.get('part', 0)
            executor = form.cleaned_data.get('executor')
            percent += part
            if executor and executor.user.username.startswith('outsourcing'):
                outsourcing_part += part
        self.instance.__outsourcing_part__ = outsourcing_part
        if self.instance.exec_status == Task.Done and percent < 100:
            self.forms[0].add_error('part', ('Вкажіть 100%% часток виконавців. Зараз : %(percent).0f%%') % {'percent': percent})
        if self.instance.project_type:
            if self.instance.project_type.executors_bonus > 0:
                bonuses_max = 100 + 100 * self.instance.project_type.owner_bonus /\
                              self.instance.project_type.executors_bonus
            else:
                bonuses_max = 100
            if percent > bonuses_max:
                self.forms[0].add_error('part', ('Сума часток виконавців не має перевищувати %(bonuses_max).0f%%. '
                                        'Зараз : %(percent).0f%%') % {'bonuses_max': bonuses_max, 'percent': percent})


ExecutorsFormSet = inlineformset_factory(Task, Execution, form=ExecutorInlineForm, extra=1, formset=ExecutorsInlineFormset)

class OrderInlineForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['contractor', 'deal_number', 'value', 'advance', 'pay_status', 'pay_date']
        widgets = {
            'contractor': Select2Widget(attrs={'data-width': '100%'}),
            'pay_date': AdminDateWidget(),
            'DELETION_FIELD_NAME': forms.HiddenInput()
        }

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
            if form.is_valid():
                outsourcing += form.cleaned_data.get('value', 0)
        if self.instance.exec_status == Task.Done:
            if self.instance.project_type.net_price() > 0 and hasattr(self.instance, '__outsourcing_part__'):
                costs_part = outsourcing / self.instance.project_type.net_price() * 100
                if self.instance.__outsourcing_part__ > 0 and costs_part == 0:
                    self.forms[0].add_error(None, 'Добавте витрати по аутсорсингу')
                if self.instance.__outsourcing_part__ < costs_part:
                    self.forms[0].add_error(None, 'Відсоток витрат на аутсорсинг перевищує відсоток виконання робіт аутсорсингом')
            elif self.instance.project_type.net_price() == 0 and outsourcing > 0:
                self.forms[0].add_error(None, 'У проекту вартість якого дорівнює нулю не може бути витрат')


CostsFormSet = inlineformset_factory(Task, Order, form=OrderInlineForm, extra=1, formset=CostsInlineFormset)


SendingFormSet = inlineformset_factory(Task, Sending, fields=('receiver', 'receipt_date', 'copies_count', 'register_num'),
                                       extra=1, widgets={'receiver': Select2Widget(attrs={'data-width': '100%'}), 'receipt_date': AdminDateWidget(), 'DELETION_FIELD_NAME': forms.HiddenInput()})


class TaskFilterForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super(TaskFilterForm, self).__init__(*args, **kwargs)
        exec_status = []
        exec_status.insert(0, (0, "Всі"))
        exec_status.insert(1, ('IW', "В черзі"))
        exec_status.insert(2, ('IP', "Виконується"))
        exec_status.insert(3, ('HD', "Виконано"))
        exec_status.insert(4, ('ST', "Надіслано"))

        owners = [(owner[0], owner[1]) for owner in Task.objects.values_list('owner__id', 'owner__name').distinct()]
        owners.insert(0, (0, "Всі"))
        customers = [(customer.id, customer.name) for customer in Customer.objects.all()]
        customers.insert(0, (0, "Всі"))

        self.fields['exec_status'].choices = exec_status
        self.fields['owner'].choices = owners
        self.fields['customer'].choices = customers

    exec_status = forms.ChoiceField(label='Статус виконання', required=False, widget=forms.Select(attrs={"onChange": 'submit()'}))
    owner = forms.ChoiceField(label='Керівник проекту', required=False, widget=forms.Select(attrs={"onChange": 'submit()'}))
    customer = forms.ChoiceField(label='Замовник', required=False, widget=forms.Select(attrs={"onChange": 'submit()'}))
    filter = forms.CharField(label='Слово пошуку', max_length=255, required=False)
