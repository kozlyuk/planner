from django.urls import path

from . import views


urlpatterns = [
    path('kpi/recalc/', views.KpiRecalc.as_view(), name='kpi_recalc'),
    path('report/', views.ReportView.as_view(), name='report_form'),
    path('report/render/', views.ReportRender.as_view(), name='report_render'),

    path('customer_chart/', views.CustomerChartView.as_view(), name='customer_chart_form'),
    path('customer_chart/render/', views.CustomerChartRender.as_view(), name='customer_chart_render'),
    path('employee_chart/', views.EmployeeChartView.as_view(), name='employee_chart_form'),
    path('employee_chart/render/', views.EmployeeChartRender.as_view(), name='employee_chart_render'),
]
