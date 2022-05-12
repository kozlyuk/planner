from django.urls import path, include
from rest_framework import routers

from . import api


router = routers.DefaultRouter()
router.register("task", api.TaskViewSet, basename='Task')
router.register("project", api.ProjectViewSet, basename='Project')
router.register("employee", api.EmployeeViewSet, basename='Employee')

urlpatterns = (
    path("", include(router.urls)),
)
