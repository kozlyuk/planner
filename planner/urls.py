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
from planner import views
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.conf import settings
from django.views.i18n import JavaScriptCatalog
from .views import DealList, DealUpdate, DealCreate, DealDelete, DealCalculation
from .views import TaskList, TaskUpdate, TaskCreate, TaskDelete, TaskDetail, TaskExchange
from .views import EmployeeUpdate, SubtaskUpdate, InttaskDetail
from .views import NewsList, NewsDetail, NewsUpdate, NewsCreate, NewsDelete
from .views import EventList, EventDetail, EventUpdate, EventCreate, EventDelete

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin/jsi18n', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico')),

    url(r'^$', views.home_page, name='home_page'),

    url(r'^deal/$', DealList.as_view(), name='deal_list'),
    url(r'^deal/(?P<pk>\d+)/change/$', DealUpdate.as_view(), name='deal_update'),
    url(r'^deal/add/$', DealCreate.as_view(), name='deal_add'),
    url(r'^deal/(?P<pk>[0-9]+)/delete/$', DealDelete.as_view(), name='deal_delete'),
    url(r'^deal/(?P<deal_id>\d+)/calculation/$', DealCalculation.as_view(), name='calculation'),

    url(r'^project/$', TaskList.as_view(), name='task_list'),
    url(r'^project/(?P<pk>\d+)/change/$', TaskUpdate.as_view(), name='task_update'),
    url(r'^project/add/$', TaskCreate.as_view(), name='task_add'),
    url(r'^project/(?P<pk>\d+)/delete/$', TaskDelete.as_view(), name='task_delete'),
    url(r'^project/(?P<pk>\d+)/$', TaskDetail.as_view(), name='task_detail'),
    url(r'^project/exchange/$', TaskExchange.as_view(), name='task_exchange'),

    url(r'^subtask/(?P<pk>\d+)/$', SubtaskUpdate.as_view(), name='subtask_form'),
    url(r'^inttask/(?P<pk>\d+)/$', InttaskDetail.as_view(), name='inttask_detail'),
    url(r'^login/$', views.login_page, name='login_page'),
    url(r'^logout/$', views.logout_page, name='logout_page'),

    url(r'^employee/(?P<employee_id>\d+)/bonus/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        BonusesList.as_view(), name='bonus_calc'),
    url(r'^employee/change/$', EmployeeUpdate.as_view(), name='employee_update'),

    url(r'^news/$', NewsList.as_view(), name='news_list'),
    url(r'^news/(?P<pk>\d+)/detail/$', NewsDetail.as_view(), name='news_detail'),
    url(r'^news/(?P<pk>\d+)/change/$', NewsUpdate.as_view(), name='news_update'),
    url(r'^news/add/$', NewsCreate.as_view(), name='news_add'),
    url(r'^news/(?P<pk>\d+)/delete/$', NewsDelete.as_view(), name='news_delete'),

    url(r'^event/$', EventList.as_view(), name='event_list'),
    url(r'^event/(?P<pk>[0-9]+)/detail/$', EventDetail.as_view(), name='event_detail'),
    url(r'^event/(?P<pk>[0-9]+)/change/$', EventUpdate.as_view(), name='event_update'),
    url(r'^event/add/$', EventCreate.as_view(), name='event_add'),
    url(r'^event/(?P<pk>[0-9]+)/delete/$', EventDelete.as_view(), name='event_delete'),
    url(r'^deal/calculation/', DealCalc.as_view(), name='deal_calc'), ## temporary url
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]