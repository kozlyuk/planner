from rest_framework import viewsets, permissions

from . import serializers
from planner.filters import employee_queryset_filter, task_queryset_filter, execuition_queryset_filter


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Task class
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Filter queryset by owner ('owner' get parameter)
    Filter queryset by executor ('executor' get parameter)
    Filter queryset by company ('company' get parameter)
    Filter queryset by planned_start ('planned_start' get parameter)
    Filter queryset by planned_finish ('planned_finish' get parameter)
    Filter queryset by search_string ('filter' get parameter)
    Order queryset by any given field ('o' get parameter)
    """

    serializer_class = serializers.TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'options']

    def get_queryset(self):
        # filtering queryset
        queryset, _, _ = execuition_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Project class
    Filter queryset by search_string ('filter' get parameter)
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by owners ('owner' get parameters list)
    Filter queryset by customers ('customer' get parameters list)
    Filter queryset by constructions ('construction' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Order queryset by any given field ('o' get parameter)
    """

    serializer_class = serializers.ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'options']

    def get_queryset(self):
        # filtering queryset
        queryset = task_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Execution class grouped by emplyees
    Filter queryset by exec_statuses ('exec_status' get parameters list)
    Filter queryset by work_types ('work_type' get parameters list)
    Filter queryset by owner ('owner' get parameter)
    Filter queryset by company ('company' get parameter)
    Filter queryset by planned_start ('planned_start' get parameter)
    Filter queryset by planned_finish ('planned_finish' get parameter)
    Filter queryset by search_string ('filter' get parameter)
    Order queryset by any given field ('o' get parameter)
    """

    serializer_class = serializers.EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'options']

    def get_queryset(self):
        # filtering queryset
        queryset = employee_queryset_filter(self.request.user, self.request.GET)
        # return filtered queryset
        return queryset
