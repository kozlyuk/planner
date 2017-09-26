# -*- encoding: utf-8 -*-
from django import forms
from planner.models import User, Project, Task, Deal, Customer


class UserLoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'password')

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
    def __init__(self, user, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['project_type'].queryset = Project.objects.all()
        self.fields['deal'].queryset = Deal.objects.all()

    class Meta:
        model = Task
        exclude = ('planned_start', 'planned_finish', 'actual_start', 'actual_finish')


class TaskFilterForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super(TaskFilterForm, self).__init__(*args, **kwargs)
        exec_status = []
        exec_status.insert(0, (0, "Всі"))
        exec_status.insert(1, ('IL', "В черзі"))
        exec_status.insert(2, ('IP', "Виконується"))
        exec_status.insert(3, ('HD', "Виконано"))

        owners = [(owner[0], owner[1]) for owner in Task.objects.values_list('owner__id', 'owner__name').distinct()]
        owners.insert(0, (0, "Всі"))
        customers = [(customer.id, customer.name) for customer in Customer.objects.all()]
        customers.insert(0, (0, "Всі"))

        self.fields['exec_status'].choices = exec_status
        self.fields['owner'].choices = owners
        self.fields['customer'].choices = customers

    exec_status = forms.ChoiceField(label='Статус виконання', required=False, widget=forms.Select(attrs={"onChange":'submit()'}))
    owner = forms.ChoiceField(label='Керівник проекту', required=False, widget=forms.Select(attrs={"onChange":'submit()'}))
    customer = forms.ChoiceField(label='Замовник', required=False, widget=forms.Select(attrs={"onChange":'submit()'}))
    filter = forms.CharField(label='Слово пошуку', max_length=255, required=False)
