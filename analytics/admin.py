from django.contrib import admin
from analytics.models import Kpi


@admin.register(Kpi)
class KpiAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period', 'name', 'value']
