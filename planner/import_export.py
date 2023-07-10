import re
import operator
import tablib
from functools import reduce

from django.db.models import Q
from django import forms
from crum import get_current_user
from import_export.forms import ImportForm, ConfirmImportForm
from import_export import resources
from import_export.fields import Field
from import_export.widgets import DateWidget
from import_export.formats import base_formats

from .models import Task, Project, Employee, Deal, WorkType, Construction, \
                    Company, Customer, Contractor, Payment, OrderPayment, Order


class CSV(base_formats.CSV):

    def create_dataset(self, in_stream, **kwargs):
        kwargs['delimiter'] = ';'
        kwargs['format'] = 'csv'
        return tablib.import_set(in_stream, **kwargs)


class TaskResource(resources.ModelResource):

    period = Field(attribute='period', column_name='period',
        widget=DateWidget(format='%d.%m.%Y'))

    class Meta:
        model = Task
        fields = ('object_code', 'object_address', 'project_type', 'owner',
                  'period', 'construction', 'deal', 'work_type')
        # use_bulk= True

    def get_instance(self, instance_loader, row):
        return False

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        # override to set the value of the dropdown onto the row instance
        instance.deal = kwargs.get("deal")
        instance.work_type = kwargs.get("work_type")
        # instance.creator = get_current_user()

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


class PaymentResource(resources.ModelResource):

    date = Field(attribute='date', column_name='date',
        widget=DateWidget(format='%d.%m.%Y'))

    class Meta:
        model = Payment
        import_id_fields = ['doc_number']
        fields = ['date', 'value', 'purpose', 'doc_number', 'deal', 'payer', 'receiver']
        skip_unchanged = True
        # report_skipped = False

    def before_import_row(self, row, row_number=None, **kwargs):
        """ prepare rows for import """
        row["date"] = row["Дата операції"].split()[0]
        row["value"] = row["Кредит"] or row["Дебет"]
        row["purpose"] = row["Призначення платежу"]
        row["doc_number"] = row["Документ"]
        company = None
        customer = None
        try:
            customer = Customer.objects.get(edrpou=row["ЄДРПОУ кореспондента"])
            row["payer"] = customer.pk
            company = Company.objects.get(edrpou=row["ЄДРПОУ"])
            row["receiver"] = company.pk
        except:
            pass

        purpose_nums = list(set(re.findall('[0-9-/]{5,15}', row["purpose"])))
        if row["Кредит"] and purpose_nums and company and customer:
            deals = Deal.objects.exclude(pay_status=Deal.PaidUp) \
                                .filter(company=company, customer=customer) \
                                .filter(reduce(operator.or_, (Q(number__contains=x) for x in purpose_nums)))
            if deals.count() == 1:
                row["deal"] = deals.first().pk

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """ skip some rows """
        if original.pk:
            return True
        if row["Кредит"] == '' or row["Документ"] == 'bn':
            return True
        if instance.receiver and instance.receiver.ignoreedrpou_set.filter(edrpou=row["ЄДРПОУ кореспондента"]).exists():
            return True
        return False


class OrderPaymentResource(resources.ModelResource):

    date = Field(attribute='date', column_name='date',
        widget=DateWidget(format='%d.%m.%Y'))

    class Meta:
        model = OrderPayment
        import_id_fields = ['doc_number']
        fields = ['date', 'value', 'purpose', 'doc_number', 'order', 'payer', 'receiver']
        skip_unchanged = True
        # report_skipped = False

    def before_import_row(self, row, row_number=None, **kwargs):
        """ prepare rows for import """
        row["date"] = row["Дата операції"].split()[0]
        row["value"] = row["Кредит"] or row["Дебет"]
        row["purpose"] = row["Призначення платежу"]
        row["doc_number"] = row["Документ"]
        company = None
        contractor = None
        try:
            company = Company.objects.get(edrpou=row["ЄДРПОУ"])
            row["payer"] = company.pk
            contractor = Contractor.objects.get(edrpou=row["ЄДРПОУ кореспондента"])
            row["receiver"] = contractor.pk
        except:
            pass

        purpose_nums = list(set(re.findall('[0-9-/]{5,15}', row["purpose"])))
        if row["Дебет"] and purpose_nums and company and contractor:
            orders = Order.objects.exclude(pay_status=Order.PaidUp) \
                                  .filter(company=company, contractor=contractor) \
                                  .filter(reduce(operator.or_, (Q(deal_number__contains=x) for x in purpose_nums)))
            if orders.count() == 1:
                row["order"] = orders.first().pk

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """ skip some rows """
        if original.pk:
            return True
        if row["Дебет"] == '' or row["Документ"] == 'bn':
            return True
        if instance.payer and instance.payer.ignoreedrpou_set.filter(edrpou=row["ЄДРПОУ кореспондента"]).exists():
            return True
        return False
