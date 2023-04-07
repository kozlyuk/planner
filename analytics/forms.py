from datetime import date
from django import forms
from django_select2.forms import Select2Widget, Select2MultipleWidget

from planner.models import Company, Customer, Employee
from .models import Report, Chart
from html_templates.models import HTMLTemplate


def current_year():
    return date.today().year

def year_choices():
    return [(r,r) for r in range(2015, date.today().year+1)]


class ReportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        report = [(report.id, report.name) for report in Report.objects.filter(template__document_type=HTMLTemplate.Report)]
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

class CustomerChartForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        chart = [(chart.id, chart.name) for chart in Chart.objects.filter(
            template__document_type=HTMLTemplate.Chart,
            content_type__model='customer'
            )]
        customer = [(customer.id, customer.name) for customer in Customer.objects.filter(active=True)]
        self.fields['chart'].choices = chart
        self.fields['customer'].choices = customer

    chart = forms.ChoiceField(label='Діаграма', widget=Select2Widget(), required=True)
    customer = forms.ChoiceField(label='Замовник', widget=Select2MultipleWidget(), required=False)
    year = forms.TypedChoiceField(coerce=int, choices=year_choices, initial=current_year)


class EmployeeChartForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        chart = [(chart.id, chart.name) for chart in Chart.objects.filter(
            template__document_type=HTMLTemplate.Chart,
            content_type__model='employee'
            )]
        employee = [(customer.id, customer.name) for customer in Employee.objects.filter(user__is_active=True)]
        self.fields['chart'].choices = chart
        self.fields['employee'].choices = employee

    chart = forms.ChoiceField(label='Діаграма', widget=Select2Widget(), required=True)
    employee = forms.ChoiceField(label='Працівник', widget=Select2MultipleWidget(), required=False)
    year = forms.TypedChoiceField(coerce=int, choices=year_choices, initial=current_year)
