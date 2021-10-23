from django.urls import path

from . import views

urlpatterns = [
    path('deal/<int:deal_id>/calculation/', views.DealCalc.as_view(), name='calculation'),
    path('deal/<int:deal_id>/render/', views.DealRender.as_view(), name='deal_render'),
    path('deal/<int:deal_id>/generate_pdf/', views.DealGeneratePDF.as_view(), name='deal_generate_pdf'),

    path('employee/<int:employee_id>/bonus/<int:year>/<int:month>/',
         views.BonusesCalc.as_view(), name='bonus_calc'),

]
