"""planner URL Configuration"""

from django.urls import path
from django.urls import include
from django.contrib import admin
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.i18n import JavaScriptCatalog
from planner import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/jsi18n', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico')),

    path('', views.Dashboard.as_view(), name='home_page'),

    path('deal/', views.DealList.as_view(), name='deal_list'),
    path('deal/<int:pk>/change/', views.DealUpdate.as_view(), name='deal_update'),
    path('deal/add/', views.DealCreate.as_view(), name='deal_add'),
    path('deal/<int:pk>/delete/', views.DealDelete.as_view(), name='deal_delete'),
    path('deal/<int:deal_id>/calculation/', views.DealCalc.as_view(), name='calculation'),

    path('project/', views.TaskList.as_view(), name='task_list'),
    path('project/<int:pk>/change/', views.TaskUpdate.as_view(), name='task_update'),
    path('project/add/', views.TaskCreate.as_view(), name='task_add'),
    path('project/<int:pk>/delete/', views.TaskDelete.as_view(), name='task_delete'),
    path('project/<int:pk>/', views.TaskDetail.as_view(), name='task_detail'),
    path('project/exchange/', views.TaskExchange.as_view(), name='task_exchange'),

    #path('sprint/<int:year>/week/<int:week>/', views.SprintList.as_view(), name='sprint_list'),
    path('sprint/', views.SprintList.as_view(), name='sprint_list'),

    path('execution/<int:pk>/status/<str:status>/',
         views.ExecutionStatusChange.as_view(), name='execution_status_change'),

    path('receiver/', views.ReceiverList.as_view(), name='receiver_list'),
    path('receiver/add', views.ReceiverCreate.as_view(), name='receiver_add'),
    path('receiver/<int:pk>/change/', views.ReceiverUpdate.as_view(), name='receiver_update'),
    path('receiver/<int:pk>/delete/', views.ReceiverDelete.as_view(), name='receiver_delete'),

    path('project/types/', views.ProjectList.as_view(), name='project_type_list'),
    path('project/types/add/', views.ProjectCreate.as_view(), name='project_type_add'),
    path('project/types/<int:pk>/change/', views.ProjectUpdate.as_view(), name='project_type_update'),
    path('project/types/<int:pk>/delete/', views.ProjectDelete.as_view(), name='project_type_delete'),
    # path('project/registry/', views.TaskRegistry.as_view(), name='task_registry'),

    path('customer/', views.CustomerList.as_view(), name='customer_list'),
    path('customer/add', views.CustomerCreate.as_view(), name='customer_add'),
    path('customer/<int:pk>/change/', views.CustomerUpdate.as_view(), name='customer_update'),
    path('customer/<int:pk>/delete/', views.CustomerDelete.as_view(), name='customer_delete'),

    path('company/', views.CompanyList.as_view(), name='company_list'),
    path('company/add', views.CompanyCreate.as_view(), name='company_add'),
    path('company/<int:pk>/change/', views.CompanyUpdate.as_view(), name='company_update'),
    path('company/<int:pk>/delete/', views.CompanyDelete.as_view(), name='company_delete'),

    path('contractor/', views.ContractorList.as_view(), name='contractor_list'),
    path('contractor/add', views.ContractorCreate.as_view(), name='contractor_add'),
    path('contractor/<int:pk>/change/', views.ContractorUpdate.as_view(), name='contractor_update'),
    path('contractor/<int:pk>/delete/', views.ContractorDelete.as_view(), name='contractor_delete'),

    path('subtask/<int:pk>/', views.SubtaskDetail.as_view(), name='subtask_detail'),
    path('inttask/<int:pk>/', views.InttaskDetail.as_view(), name='inttask_detail'),
    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_page, name='logout_page'),

    path('colleagues/', views.СolleaguesList.as_view(), name='colleagues_list'),
    path('colleagues/<int:pk>/detail/', views.СolleaguesDetail.as_view(), name='colleagues_detail'),

    path('employee/', views.EmployeeList.as_view(), name='employee_list'),
    path('employee/add', views.EmployeeCreate.as_view(), name='employee_add'),
    path('employee/<int:pk>/change/', views.EmployeeUpdate.as_view(), name='employee_update'),
    path('employee/change/', views.EmployeeSelfUpdate.as_view(), name='employee_self_update'),
    path('employee/<int:employee_id>/bonus/<int:year>/<int:month>/',
         views.BonusesCalc.as_view(), name='bonus_calc'),

    path('news/', views.NewsList.as_view(), name='news_list'),
    path('news/<int:pk>/detail/', views.NewsDetail.as_view(), name='news_detail'),
    path('news/<int:pk>/change/', views.NewsUpdate.as_view(), name='news_update'),
    path('news/add/', views.NewsCreate.as_view(), name='news_add'),
    path('news/<int:pk>/delete/', views.NewsDelete.as_view(), name='news_delete'),

    path('event/', views.EventList.as_view(), name='event_list'),
    path('event/<int:pk>/detail/', views.EventDetail.as_view(), name='event_detail'),
    path('event/<int:pk>/change/', views.EventUpdate.as_view(), name='event_update'),
    path('event/add/', views.EventCreate.as_view(), name='event_add'),
    path('event/<int:pk>/delete/', views.EventDelete.as_view(), name='event_delete'),


    path('select2/', include('django_select2.urls')),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
