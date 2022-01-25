from datetime import datetime
from django.contrib import admin
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django_object_actions import DjangoObjectActions
from urllib.parse import parse_qs
from django.shortcuts import HttpResponseRedirect

from .models import Kpi, Report
from .tasks import recalc_kpi

@admin.register(Kpi)
class KpiAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = ['employee', 'period', 'name', 'value', 'modified']
    date_hierarchy = 'period'
    list_filter = [('employee', RelatedDropdownFilter), 'name']

    def kpi_recalc(modeladmin, request, queryset):
        period = None
        changelist_filters = parse_qs(request.GET.get('_changelist_filters'))
        period__month = changelist_filters['period__month'][0]
        period__year = changelist_filters['period__year'][0]
        if period__month and period__year:
            period = datetime(year=int(period__year), month=int(period__month), day=1).date()

        recalc_kpi(period=period)

        return HttpResponseRedirect(f"/admin/analytics/kpi/?period__month={period__month}&period__year={period__year}")

    kpi_recalc.label = "Перерахувати КПЕ"
    changelist_actions = ('kpi_recalc', )


@admin.register(Report)
class ReportAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = ['name', 'template']
