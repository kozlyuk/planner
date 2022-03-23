from datetime import date, timedelta
from django import forms
from django_select2.forms import Select2Widget

from planner.models import Company, Customer
from .models import Report


class ReportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        report = [(report.id, report.name) for report in Report.objects.all()]
        company = [(company.id, company.name) for company in Company.objects.filter(active=True)]
        customer = [(customer.id, customer.name) for customer in Customer.objects.filter(active=True)]
        self.fields['report'].choices = report
        self.fields['company'].choices = company
        self.fields['customer'].choices = customer

    report = forms.ChoiceField(label='Звіт', widget=Select2Widget())
    company = forms.ChoiceField(label='Компанія', widget=Select2Widget())
    customer = forms.ChoiceField(label='Замовник', widget=Select2Widget())
    from_date = forms.DateField(label='Дата початку',
                                widget=forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
                                required=False
                                )
    to_date = forms.DateField(label='Дата завершення',
                              widget=forms.DateInput(format=('%Y-%m-%d'), attrs={'type': 'date'}),
                              required=False
                              )
