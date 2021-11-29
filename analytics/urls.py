from django.urls import path

from . import views


urlpatterns = [
    path('kpi/recalc/', views.KpiRecalc.as_view(), name='kpi_recalc'),

]
