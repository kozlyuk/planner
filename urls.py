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
from django.contrib import admin
from planner import views
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.conf import settings

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico')),

    url(r'^$', views.home_page, name='home_page'),
    url(r'^project/$', views.projects_list, name='projects_list'),
    url(r'^project/add/$', views.project_details, name='project_add'),
    url(r'^project/(?P<project_id>\d+)/$', views.project_details, name='project_details'),
    url(r'^project/(?P<project_id>\d+)/edit/$', views.project_form, name='project_form'),
    url(r'^deal/(?P<deal_id>\d+)/calculation/$', views.calculation, name='calculation'),
    url(r'^employee/(?P<employee_id>\d+)/bonus/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        views.bonus_calc, name='bonus_calc'),
    url(r'^deal/$', views.deals_list, name='deals_list'),
    url(r'^login/$', views.login_page, name='login_page'),
    url(r'^logout/$', views.logout_page, name='logout_page'),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)