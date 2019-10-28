from django.contrib import admin
from analytics.models import Bonus, KpiName, Kpi


@admin.register(KpiName)
class KpiNameAdmin(admin.ModelAdmin):
    list_display = ['name']
    fieldsets = [
        (None, {'fields': ['name',
                           ]})
        ]
