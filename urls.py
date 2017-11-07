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
from django.conf.urls import url, include
from django.contrib import admin
from planner import views
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.conf import settings
from .views import NewsList, NewsCreate, NewsDetail, NewsUpdate, NewsDelete
from .views import EventList, EventCreate, EventDetail, EventUpdate, EventDelete
from .views import ProjectUpdate

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico')),
    #url(r'^select2/', include('django_select2.urls')),

    url(r'^$', views.home_page, name='home_page'),
    url(r'^project/$', views.projects_list, name='projects_list'),
    #url(r'^project/$', RedirectView.as_view(url='/admin/planner/task/'), name='projects_list'),
    url(r'^project/(?P<pk>[0-9]+)/change/$', ProjectUpdate.as_view(), name='project_update'),
    url(r'^project/(?P<project_id>\d+)/$', views.project_detail, name='project_detail'),
    #url(r'^project/(?P<project_id>\d+)/edit/$', views.project_form, name='project_form'),
    url(r'^inttask/(?P<task_id>\d+)/$', views.inttask_detail, name='inttask_detail'),
    # url(r'^deal/$', views.deals_list, name='deals_list'),
    url(r'^deal/$', RedirectView.as_view(url='/admin/planner/deal/'), name='deals_list'),
    url(r'^login/$', views.login_page, name='login_page'),
    url(r'^logout/$', views.logout_page, name='logout_page'),

    url(r'^deal/(?P<deal_id>\d+)/calculation/$', views.calculation, name='calculation'),
    url(r'^employee/(?P<employee_id>\d+)/bonus/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        views.bonus_calc, name='bonus_calc'),
    url(r'^news/$', NewsList.as_view(), name='news_list'),
    url(r'^news/(?P<pk>[0-9]+)/detail/$', NewsDetail.as_view(), name='news_detail'),
    url(r'^news/(?P<pk>[0-9]+)/change/$', NewsUpdate.as_view(), name='news_update'),
    url(r'^news/add/$', NewsCreate.as_view(), name='news_add'),
    url(r'^news/(?P<pk>[0-9]+)/delete/$', NewsDelete.as_view(), name='news_delete'),

    url(r'^event/$', EventList.as_view(), name='event_list'),
    url(r'^event/(?P<pk>[0-9]+)/detail/$', EventDetail.as_view(), name='event_detail'),
    url(r'^event/(?P<pk>[0-9]+)/change/$', EventUpdate.as_view(), name='event_update'),
    url(r'^event/add/$', EventCreate.as_view(), name='event_add'),
    url(r'^event/(?P<pk>[0-9]+)/delete/$', EventDelete.as_view(), name='event_delete'),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)