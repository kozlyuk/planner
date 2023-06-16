from import_export.forms import ImportForm, ConfirmImportForm
from import_export import resources
from import_export.fields import Field
from crum import get_current_user
from django import forms

from .models import Task, Project, Employee, Deal, WorkType, Construction



class TaskResource(resources.ModelResource):

    class Meta:
        model = Task
        fields = ('object_code', 'object_address', 'project_type', 'owner',
                  'period', 'construction', 'deal', 'work_type')
        use_bulk= True

    def get_instance(self, instance_loader, row):
        return False

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        # override to set the value of the dropdown onto the row instance
        instance.deal = kwargs.get("deal")
        instance.work_type = kwargs.get("work_type")
        instance.creator = get_current_user()

    def before_import_row(self, row, row_number=None, **kwargs):
        project_type = Project.objects.get(price_code=row["project_type"])
        row["project_type"] = project_type.pk
        owner = Employee.objects.get(name=row["owner"])
        row["owner"] = owner.pk
        construction = Construction.objects.get(name_eng=row["construction"])
        row["construction"] = construction.pk


class CustomImportForm(ImportForm):
    deal = forms.ModelChoiceField(
        queryset=Deal.objects.filter(act_status=Deal.NotIssued),
        required=True)
    work_type = forms.ModelChoiceField(
        queryset=WorkType.objects.all(),
        required=True)


class CustomConfirmImportForm(ConfirmImportForm):
    deal = forms.ModelChoiceField(
        queryset=Deal.objects.filter(act_status=Deal.NotIssued),
        required=True)
    work_type = forms.ModelChoiceField(
        queryset=WorkType.objects.all(),
        required=True)
