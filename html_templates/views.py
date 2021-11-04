from datetime import date
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from planner.models import Deal, Employee
from .context import context_deal_calculation, context_bonus_per_month
# from .tasks import generate_pdf
from .context import context_deal_calculation


@method_decorator(login_required, name='dispatch')
class DealCalc(TemplateView):
    """ View for displaying calculation to a deal """
    template_name = "deal_calc.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deal = Deal.objects.get(id=self.kwargs['deal_id'])
        context_deal = context_deal_calculation(deal)

        return {**context, **context_deal}


@method_decorator(login_required, name='dispatch')
class BonusesCalc(TemplateView):
    """ View for displaying bonuses calculation to a employee """
    template_name = "bonuses_list.html"

    def dispatch(self, request, *args, **kwargs):
        employee = Employee.objects.get(id=self.kwargs['employee_id'])
        if request.user.is_superuser or request.user == employee.user or request.user == employee.head.user \
                or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = Employee.objects.get(id=self.kwargs['employee_id'])
        period = date(year=kwargs['year'], month=kwargs['month'], day=1)
        context_bonus = context_bonus_per_month(employee, period)

        return {**context, **context_bonus}


@method_decorator(login_required, name='dispatch')
class DealRender(TemplateView):
    """ View for rendering a deal """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deal = Deal.objects.get(id=self.kwargs['deal_id'])
        context_deal = context_deal_calculation(deal)

        return {**context, **context_deal}

    def render_to_response(self, context):
        template = context['deal'].customer.deal_template

        if template:
            return HttpResponse(template.render(context))
        else:
            return HttpResponse('HTML template does not exist for this customer')


@method_decorator(login_required, name='dispatch')
class DealGeneratePDF(View):
    """ Generating PDF copy for Deal """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        try:
            deal = Deal.objects.get(pk=kwargs['deal_id'])
            # generate_pdf(deal.customer.deal_template,
            #              context_deal_calculation(deal),
            #              Deal,
            #              deal.pk
            #              )
            return redirect(reverse('deal_update', args=[deal.pk]))
        except Deal.DoesNotExist:
            return HttpResponse('Deal object does not exist')
