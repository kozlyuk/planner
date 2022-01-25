from django.urls import path

from . import views


urlpatterns = [
    path('kpi/recalc/', views.KpiRecalc.as_view(), name='kpi_recalc'),
    path('report/', views.ReportView.as_view(), name='report_form'),
    path('report/render/', views.ReportRender.as_view(), name='report_render'),
    path('report/generate_pdf/', views.ReportGeneratePDF.as_view(), name='report_generate_pdf'),
]
