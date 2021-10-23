from django.urls import path

from . import views

urlpatterns = [
    path('deal/<int:deal_id>/calculation/', views.DealCalc.as_view(), name='calculation'),
    path('deal/<int:deal_id>/render/', views.DealRender.as_view(), name='deal_render'),

    path('employee/<int:employee_id>/bonus/<int:year>/<int:month>/',
         views.BonusesCalc.as_view(), name='bonus_calc'),

]
