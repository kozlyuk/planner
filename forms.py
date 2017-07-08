# -*- encoding: utf-8 -*-
from django import forms
from planner.models import User, Project, Task, Deal


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
        project_types = [(p.id, "%s %s" % (p.price_code, p.project_type)) for p in Project.objects.all()]
        project_types.insert(0, (0, "Всі"))
        deals = [(r.id, "%s %s" % (r.number, r.customer.name)) for r in Deal.objects.all()]
        deals.insert(0, (0, "Всі"))

        exec_status = []
        exec_status.insert(0, (0, "Всі"))
        exec_status.insert(1, ('IW', "В очікуванні"))
        exec_status.insert(2, ('IL', "В черзі"))
        exec_status.insert(3, ('IP', "Виконується"))
        exec_status.insert(4, ('HD', "Виконано"))

        self.fields['project_type'].choices = project_types
        self.fields['deal'].choices = deals
        self.fields['exec_status'].choices = exec_status

    project_type = forms.ChoiceField()
    deal = forms.ChoiceField()
    exec_status = forms.ChoiceField()

    object_code = forms.CharField(max_length=255)
    object_address = forms.CharField(max_length=255)
    project_code = forms.CharField(max_length=255)

