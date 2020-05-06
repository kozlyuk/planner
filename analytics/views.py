from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView
from django.core.exceptions import PermissionDenied

from planner.models import Employee
from analytics.models import Kpi


@method_decorator(login_required, name='dispatch')
class KpiShow(TemplateView):
    """ View for displaying KPIs for employees """
    template_name = "kpi_list.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='ГІПи').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = Employee.objects.all()

        tasks = Kpi.objects.filter(actual_finish__month=self.kwargs['month'],
                                   actual_finish__year=self.kwargs['year']) \
                           .order_by('employee')

        context['first_name'] = employee.user.first_name
        context['tasks'] = tasks
        return context
