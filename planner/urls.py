"""planner URL Configuration"""

from django.urls import path
from django.urls import include
from django.contrib import admin
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.conf import settings
from django.views.i18n import JavaScriptCatalog
from planner import views

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('sentry-debug/', trigger_error),

    path('admin/', admin.site.urls),
    path('admin/jsi18n', JavaScriptCatalog.as_view(), name='javascript-catalog'),

    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_page, name='logout_page'),
    path('', views.Dashboard.as_view(), name='home_page'),

    path('deal/', views.DealList.as_view(), name='deal_list'),
    path('deal/<int:pk>/change/', views.DealUpdate.as_view(), name='deal_update'),
    path('deal/add/', views.DealCreate.as_view(), name='deal_add'),
    path('deal/<int:pk>/delete/', views.DealDelete.as_view(), name='deal_delete'),

    path('project/', views.TaskList.as_view(), name='task_list'),
    path('project/<int:pk>/change/', views.TaskUpdate.as_view(), name='task_update'),
    path('project/add/', views.TaskCreate.as_view(), name='task_add'),
    path('project/<int:pk>/delete/', views.TaskDelete.as_view(), name='task_delete'),
    path('project/<int:pk>/', views.TaskDetail.as_view(), name='task_detail'),
    path('project/exchange/', views.TaskExchange.as_view(), name='task_exchange'),

    #path('sprint/<int:year>/week/<int:week>/', views.SprintList.as_view(), name='sprint_list'),
    path('sprint/', views.SprintList.as_view(), name='sprint_list'),
    path('execution/<int:pk>/status/<str:status>/<str:prev_status>/',
         views.ExecutionStatusChange.as_view(), name='execution_status_change'),
    path('execution/update/<int:pk>', views.ExecutionUpdateModal.as_view(), name='execution_update'),

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

    path('colleague/', views.СolleagueList.as_view(), name='colleague_list'),
    path('colleague/<int:pk>/detail/', views.СolleagueDetail.as_view(), name='colleague_detail'),

    path('employee/', views.EmployeeList.as_view(), name='employee_list'),
    path('employee/add', views.EmployeeCreate.as_view(), name='employee_add'),
    path('employee/<int:pk>/change/', views.EmployeeUpdate.as_view(), name='employee_update'),
    path('employee/change/', views.EmployeeSelfUpdate.as_view(), name='employee_self_update'),

    path('select2/', include('django_select2.urls')),
    path('api/gantt/', include('gantt.urls')),
    path('notice/', include('notice.urls')),
    path('analytics/', include('analytics.urls')),
    path('templates/', include('html_templates.urls')),

]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
