from rest_framework import viewsets, permissions

from . import serializers
from planner.views import task_queryset_filter, execuition_queryset_filter

class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for the Task class
    Filter queryset by car_id field ('car_id' get parameters list)
    Filter queryset by from_date field ('from_date' get parameter)
    Filter queryset by end_date field ('end_date' get parameter)
    Order queryset by any given field ('order' get parameter)
    """

    serializer_class = serializers.ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'options']

    def get_queryset(self):
        # filtering queryset
        queryset = task_queryset_filter(self.request)
        # return filtered queryset
        return queryset


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for the Task class
    Filter queryset by car_id field ('car_id' get parameters list)
    Filter queryset by from_date field ('from_date' get parameter)
    Filter queryset by end_date field ('end_date' get parameter)
    Order queryset by any given field ('order' get parameter)
    """

    serializer_class = serializers.ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'options']

    def get_queryset(self):
        # filtering queryset
        queryset, _, _ = execuition_queryset_filter(self.request)
        # return filtered queryset
        return queryset
