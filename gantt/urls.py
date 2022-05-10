from django.urls import path, include
from rest_framework import routers

from . import api


router = routers.DefaultRouter()
router.register("project", api.ProjectViewSet, basename='Project')
router.register("task", api.TaskViewSet, basename='Task')

urlpatterns = (
    path("", include(router.urls)),
)
