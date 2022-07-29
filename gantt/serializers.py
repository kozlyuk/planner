from rest_framework import serializers
from drf_dynamic_fields import DynamicFieldsMixin

from planner.models import Task, Employee, Execution
from planner.filters import execuition_queryset_filter


class TaskSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

    subtask_name = serializers.ReadOnlyField(source='subtask.name')
    executor_name = serializers.ReadOnlyField(source='executor.name')
    object_code = serializers.ReadOnlyField(source='task.object_code')
    exec_status = serializers.ReadOnlyField(source='get_exec_status_display')
    planned_duration = serializers.SerializerMethodField()

    class Meta:
        model = Execution
        fields = [
            "id",
            "object_code",
            "subtask_name",
            "executor_name",
            "exec_status",
            "planned_start",
            "planned_finish",
            "actual_start",
            "actual_finish",
            "planned_duration",
            "warning",
        ]

    def get_planned_duration(self, instance):
        # convert planned_duration to hours, minutes
        if instance.planned_duration:
            min, sec = divmod(instance.planned_duration.total_seconds(), 60)
            hour, min = divmod(min, 60)
            return f'{int(hour)} год {int(min)} хв'


class ProjectSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

    warning = serializers.SerializerMethodField()
    tasks = TaskSerializer(source='execution_set', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "object_code",
            "planned_start",
            "planned_finish",
            "actual_start",
            "actual_finish",
            "warning",
            "tasks",
        ]
        extra_kwargs = {
            'object_code': {'read_only': True},
        }

    def get_warning(self, instance):
        # get last comment
        return instance.get_last_comment()


class EmployeeSerializer(DynamicFieldsMixin, serializers.ModelSerializer):

    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "name",
            "tasks",
        ]

    def get_tasks(self, instance):
        # get tasks for employee using request data
        request_user = self.context['request'].user
        query_dict = self.context['request'].GET.copy()
        query_dict['executor'] = instance.pk
        executor_tasks, _, _ = execuition_queryset_filter(request_user, query_dict)
        return TaskSerializer(executor_tasks, many=True).data
