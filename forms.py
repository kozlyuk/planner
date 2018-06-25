# -*- encoding: utf-8 -*-
from django import forms
from .models import User, Task, Customer, Execution, Order, Sending, Deal, Employee, Project
from django.forms import inlineformset_factory
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

        self.fields['deal'].queryset = Deal.objects.exclude(act_status=Deal.Issued)

        if self.instance.pk is None:
            self.fields['project_type'].queryset = Project.objects.filter(active=True)
        else:
            self.fields['project_type'].queryset = Project.objects.filter(customer=self.instance.deal.customer,
                                                                          active=True)

    def clean(self):
        cleaned_data = super().clean()
        project_type = cleaned_data.get("project_type")
        deal = cleaned_data.get("deal")
        exec_status = cleaned_data.get("exec_status")
        actual_finish = cleaned_data.get("actual_finish")
        planned_finish = cleaned_data.get("planned_finish")
        pdf_copy = cleaned_data.get("pdf_copy")

        if project_type and deal:
            if deal.customer != project_type.customer:
                raise forms.ValidationError("Тип проекту не входить до можливих значень Замовника Договору")
        if exec_status in [Task.Done, Task.Sent]:
            if not actual_finish:
                raise forms.ValidationError("Вкажіть будь ласка Фактичне закінчення робіт")
            elif not pdf_copy:
                raise forms.ValidationError("Підвантажте будь ласка електронний примірник")
            elif deal.act_status == Deal.Issued:
                raise forms.ValidationError("Договір закрито, зверніться до керівника")
        if actual_finish and exec_status not in [Task.Done, Task.Sent]:
                raise forms.ValidationError("Будь ласка відмітьте Статус виконання або видаліть Дату виконання")
        if planned_finish and planned_finish > deal.expire_date:
            raise forms.ValidationError("Планова дата закінчення повинна бути меншою дати закінчення договору")


ExecutorsFormSet = inlineformset_factory(Task, Execution, fields=('executor', 'part_name', 'part', 'exec_status', 'finish_date'),
                                         extra=1, widgets={'executor': Select2Widget(), 'finish_date': AdminDateWidget(), 'DELETION_FIELD_NAME': forms.HiddenInput()})
CostsFormSet = inlineformset_factory(Task, Order, fields=('contractor', 'deal_number', 'value', 'advance', 'pay_status', 'pay_date'),
                                     extra=1, widgets={'contractor': Select2Widget(attrs={'data-width': '100%'}), 'pay_date': AdminDateWidget(), 'DELETION_FIELD_NAME': forms.HiddenInput()})
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
