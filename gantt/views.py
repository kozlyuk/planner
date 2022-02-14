import json
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import View, TemplateView
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from planner.models import Task, Execution
from planner.views import subtasks_queryset_filter


@method_decorator(login_required, name='dispatch')
class GetPlan(TemplateView):
    """
    View create dictionary with task-subtask structure for jsgantt-improved chart

    Raises:
        PermissionDenied: [if user does not have permission to gat data]

    Returns:
        context
    """

    template_name = 'gantt/main.html'

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

    def get_context_data(self, *args, **kwargs):
        """ prepare json-coded data for gantt """
        context = super().get_context_data(*args, **kwargs)
        # get subtasks_queryset_filter
        subtasks, start_date, end_date = subtasks_queryset_filter(self.request)
        projects = subtasks.values_list('task', flat=True)
        # distinct values
        projects = list(set(projects))
        # prepare dictionary
        gantt_data = {"view_mode": "project_view",
                      "start_date": str(start_date),
                      "end_date": str(end_date),
                      "projects": []}
        for index, project_id in enumerate(projects):
            project = Task.objects.get(pk=project_id)

            # add project to the dictionary
            gantt_data["projects"].append({"pk": project.pk,
                                           "object_code": project.object_code,
                                           "owner": project.owner.name,
                                           "exec_status": project.exec_status,
                                           "planned_start": str(project.planned_start),
                                           "planned_finish": str(project.planned_finish),
                                           "tasks": []})
            tasks = subtasks.filter(task=project)
            # add tasks to the project
            for task in tasks:
                gantt_data["projects"][index]["tasks"].append({"pk": task.pk,
                                                               "executor": task.executor.name,
                                                               "subtask": task.subtask.name,
                                                               "exec_status": task.exec_status,
                                                               "planned_start": str(task.planned_start),
                                                               "planned_finish": str(task.planned_finish),
                                                               "start_date": str(task.start_date),
                                                               "finish_date": str(task.finish_date)})
        context['gantt_data'] = json.dumps(gantt_data)
        return context


@method_decorator(login_required, name='dispatch')
class ChangePlan(View):
    """ View get project or task by pk and update planned_start or planned finish fields

    POST Args:
        task_type ([str], required): ["task" or "project"]
        pk ([str], required): [task or project pk]
        planned_start ([date]): [task or project planned_start]
        planned_finish ([date]): [task or project planned_finish]

    Raises:
        PermissionDenied: [if user does not have permission to change data]
        PermissionDenied: [if user does not have permission to change data]

    Returns:
        None
    """

    template_name = 'gantt/main.html'

    def dispatch(self, request, *args, **kwargs):
        # check permissions
        if request.user.is_superuser or request.user.groups.filter(name='ГІПи').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def post(self, request, *args, **kwargs):
        # get POST data
        task_type = request.POST.get("task_type")
        obj_pk = request.POST.get("pk")
        planned_start = request.POST.get("planned_start")
        planned_finish = request.POST.get("planned_finish")
        # get object
        obj = False
        if task_type and obj_pk and (planned_start or planned_finish):
            if task_type == "project":
                obj = get_object_or_404(Task, pk=obj_pk)
            elif task_type == "task":
                obj = get_object_or_404(Execution, pk=obj_pk)
            # update object
            if planned_start:
                obj.planned_start = planned_start
            if planned_finish:
                obj.planned_finish = planned_finish
            obj.save()
            return redirect(reverse('get_plan'))
        raise ValidationError('Not enough data')
