from django.urls import path

from . import views

urlpatterns = [
    path('deal/<int:deal_id>/render/', views.DealRender.as_view(), name='deal_render'),
    path('deal/<int:deal_id>/generate_pdf/', views.DealGeneratePDF.as_view(), name='deal_generate_pdf'),
    path('act/<int:act_id>/render/', views.ActRender.as_view(), name='act_render'),
    path('act/<int:act_id>/generate_pdf/', views.ActGeneratePDF.as_view(), name='act_generate_pdf'),
    path('invoice/<int:payment_id>/render/', views.InvoiceRender.as_view(), name='invoice_render'),
    path('invoice/<int:payment_id>/generate_pdf/', views.InvoiceGeneratePDF.as_view(), name='invoice_generate_pdf'),

    path('employee/<int:employee_id>/bonus/<int:year>/<int:month>/',
         views.BonusesCalc.as_view(), name='bonus_calc'),

]
