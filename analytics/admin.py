from django.contrib import admin
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from analytics.models import Kpi


@admin.register(Kpi)
class KpiAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period', 'name', 'value']
    date_hierarchy = 'period'
    list_filter = [('employee', RelatedDropdownFilter), 'name']
