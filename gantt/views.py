from django.views import View
from django.core.exceptions import PermissionDenied
from django.http import QueryDict
from django.http import JsonResponse

from planner.models import Task
from planner.views import subtasks_queryset_filter


class GetPlan(View):
    """
    View create dictionary with task-subtask structure for jsgantt-improved chart
    """

    def dispatch(self, request, *args, **kwargs):
        # get filter parameters from session
        if request.GET == {}:
            request.GET = request.GET.copy()
            request.GET = QueryDict(self.request.session.get('execution_query_string', ''))
            request.META['QUERY_STRING'] = self.request.session.get('execution_query_string', '')
        # check permissions
        if request.user.is_superuser or request.user.groups.filter(name='Проектувальники').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request):
        # prepare json-coded data for gantt
        subtasks, start_date, end_date = subtasks_queryset_filter(self.request)
        projects = subtasks.values_list('task', flat=True)
        # distinct values
        projects = list(set(projects))
        # prepare dictionary
        gantt_data = {"view_mode": "project_view",
                      "start_date": start_date,
                      "end_date": end_date,
                      "projects": []}
        for index, project_id in enumerate(projects):
            project = Task.objects.get(pk=project_id)
            # add project to the dictionary
            gantt_data["projects"].append({"pk": project.pk,
                                           "object_code": project.object_code,
                                           "owner": project.owner.name,
                                           "exec_status": project.exec_status,
                                           "planned_start": project.planned_start,
                                           "planned_finish": project.planned_start,
                                           "tasks": []})
            tasks = subtasks.filter(task=project)
            # add tasks to the project
            for task in tasks:
                gantt_data["projects"][index]["tasks"].append({"pk": task.pk,
                                                               "executor": task.executor.name,
                                                               "part_name": task.part_name,
                                                               "exec_status": task.exec_status,
                                                               "planned_start": task.planned_start,
                                                               "planned_finish": task.planned_finish,
                                                               "start_date": task.start_date,
                                                               "finish_date": task.finish_date})

        return JsonResponse(gantt_data, safe=False)
