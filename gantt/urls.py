from django.urls import path, include
from rest_framework import routers

from . import api
from . import views


router = routers.DefaultRouter()
router.register("task", api.TaskViewSet, basename='Task')
router.register("project", api.ProjectViewSet, basename='Project')
router.register("employee", api.EmployeeViewSet, basename='Employee')

urlpatterns = (
    path("", include(router.urls)),

    path('sprint/gantt/', views.GetPlan.as_view(), name='get_plan'),
    path('sprint/gantt/change/', views.ChangePlan.as_view(), name='change_plan'),

)
