from rest_framework import serializers

from planner.models import Task, Employee, Execution


class TaskSerializer(serializers.ModelSerializer):

    executor_name = serializers.ReadOnlyField(source='executor.name')
    exec_status = serializers.ReadOnlyField(source='get_exec_status_display')

    class Meta:
        model = Execution
        fields = [
            "id",
            "executor_name",
            "exec_status",
            "planned_start",
            "planned_finish",
            "planned_duration"
        ]
        extra_kwargs = {
            'planned_duration': {'read_only': True},
        }


class ProjectSerializer(serializers.ModelSerializer):

    tasks = TaskSerializer(source='execution_set', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "object_code",
            "planned_start",
            "planned_finish",
            "tasks",
        ]
        extra_kwargs = {
            'object_code': {'read_only': True},
        }


class EmployeeSerializer(serializers.ModelSerializer):

    tasks = TaskSerializer(source='execution_set', many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "name",
            "tasks",
        ]
