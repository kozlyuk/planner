"""planner URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.urls import path, include
from django.contrib import admin
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.i18n import JavaScriptCatalog
from planner import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin/jsi18n', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico')),

    url(r'^$', views.home_page, name='home_page'),

    url(r'^deal/$', views.DealList.as_view(), name='deal_list'),
    url(r'^deal/(?P<pk>\d+)/change/$',
        views.DealUpdate.as_view(), name='deal_update'),
    url(r'^deal/add/$', views.DealCreate.as_view(), name='deal_add'),
    url(r'^deal/(?P<pk>\d+)/delete/$',
        views.DealDelete.as_view(), name='deal_delete'),
    url(r'^deal/(?P<deal_id>\d+)/calculation/$',
        views.DealCalc.as_view(), name='calculation'),

    url(r'^project/$', views.TaskList.as_view(), name='task_list'),
    url(r'^project/(?P<pk>\d+)/change/$',
        views.TaskUpdate.as_view(), name='task_update'),
    url(r'^project/add/$', views.TaskCreate.as_view(), name='task_add'),
    url(r'^project/(?P<pk>\d+)/delete/$',
        views.TaskDelete.as_view(), name='task_delete'),
    url(r'^project/(?P<pk>\d+)/$', views.TaskDetail.as_view(), name='task_detail'),
    url(r'^project/exchange/$', views.TaskExchange.as_view(), name='task_exchange'),

    url(r'^sprint/$', views.SprintTaskList.as_view(), name='sprint_list'),

    url(r'^execution/(?P<pk>\d+)/status/(?P<status>[A-Z]{2})/$',
        views.ExecutionStatusChange.as_view(), name='execution_status_change'),

    url(r'^receiver/$', views.ReceiverList.as_view(), name='receiver_list'),
    url(r'^receiver/add$', views.ReceiverCreate.as_view(), name='receiver_add'),
    url(r'^receiver/(?P<pk>\d+)/change/$',
        views.ReceiverUpdate.as_view(), name='receiver_update'),
    url(r'^receiver/(?P<pk>\d+)/delete/$',
        views.ReceiverDelete.as_view(), name='receiver_delete'),

    url(r'^project/types/$', views.ProjectList.as_view(), name='project_type_list'),
    url(r'^project/types/add$', views.ProjectCreate.as_view(),
        name='project_type_add'),
    url(r'^project/types/(?P<pk>\d+)/change/$',
        views.ProjectUpdate.as_view(), name='project_type_update'),
    url(r'^project/types/(?P<pk>\d+)/delete/$',
        views.ProjectDelete.as_view(), name='project_type_delete'),
    # url(r'^project/registry/$', views.TaskRegistry.as_view(), name='task_registry'),

    url(r'^customer/$', views.CustomerList.as_view(), name='customer_list'),
    url(r'^customer/add$', views.CustomerCreate.as_view(), name='customer_add'),
    url(r'^customer/(?P<pk>\d+)/change/$',
        views.CustomerUpdate.as_view(), name='customer_update'),
    url(r'^customer/(?P<pk>\d+)/delete/$',
        views.CustomerDelete.as_view(), name='customer_delete'),

    url(r'^company/$', views.CompanyList.as_view(), name='company_list'),
    url(r'^company/add$', views.CompanyCreate.as_view(), name='company_add'),
    url(r'^company/(?P<pk>\d+)/change/$',
        views.CompanyUpdate.as_view(), name='company_update'),
    url(r'^company/(?P<pk>\d+)/delete/$',
        views.CompanyDelete.as_view(), name='company_delete'),

    url(r'^contractor/$', views.ContractorList.as_view(), name='contractor_list'),
    url(r'^contractor/add$', views.ContractorCreate.as_view(), name='contractor_add'),
    url(r'^contractor/(?P<pk>\d+)/change/$',
        views.ContractorUpdate.as_view(), name='contractor_update'),
    url(r'^contractor/(?P<pk>\d+)/delete/$',
        views.ContractorDelete.as_view(), name='contractor_delete'),

    url(r'^subtask/(?P<pk>\d+)/$',
        views.SubtaskUpdate.as_view(), name='subtask_form'),
    url(r'^inttask/(?P<pk>\d+)/$',
        views.InttaskDetail.as_view(), name='inttask_detail'),
    url(r'^login/$', views.login_page, name='login_page'),
    url(r'^logout/$', views.logout_page, name='logout_page'),

    url(r'^colleagues/$', views.СolleaguesList.as_view(), name='colleagues_list'),
    url(r'^colleagues/(?P<pk>\d+)/detail/$',
        views.СolleaguesDetail.as_view(), name='colleagues_detail'),

    url(r'^employee/$', views.EmployeeList.as_view(), name='employee_list'),
    url(r'^employee/add$', views.EmployeeCreate.as_view(), name='employee_add'),
    url(r'^employee/(?P<pk>\d+)/change/$',
        views.EmployeeUpdate.as_view(), name='employee_update'),
    url(r'^employee/change/$', views.EmployeeSelfUpdate.as_view(),
        name='employee_self_update'),
    url(r'^employee/(?P<employee_id>\d+)/bonus/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        views.BonusesCalc.as_view(), name='bonus_calc'),

    url(r'^news/$', views.NewsList.as_view(), name='news_list'),
    url(r'^news/(?P<pk>\d+)/detail/$',
        views.NewsDetail.as_view(), name='news_detail'),
    url(r'^news/(?P<pk>\d+)/change/$',
        views.NewsUpdate.as_view(), name='news_update'),
    url(r'^news/add/$', views.NewsCreate.as_view(), name='news_add'),
    url(r'^news/(?P<pk>\d+)/delete/$',
        views.NewsDelete.as_view(), name='news_delete'),

    url(r'^event/$', views.EventList.as_view(), name='event_list'),
    url(r'^event/(?P<pk>[0-9]+)/detail/$',
        views.EventDetail.as_view(), name='event_detail'),
    url(r'^event/(?P<pk>[0-9]+)/change/$',
        views.EventUpdate.as_view(), name='event_update'),
    url(r'^event/add/$', views.EventCreate.as_view(), name='event_add'),
    url(r'^event/(?P<pk>[0-9]+)/delete/$',
        views.EventDelete.as_view(), name='event_delete'),


    url(r'^select2/', include('django_select2.urls')),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
