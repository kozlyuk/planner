from datetime import date
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView, View
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from planner.models import ActOfAcceptance, Deal, Employee, Payment
from .context import context_deal_render, context_bonus_per_month
from .tasks import generate_pdf
from .context import context_deal_render, context_act_render, context_invoice_render


@method_decorator(login_required, name='dispatch')
class BonusesCalc(TemplateView):
    """ View for displaying bonuses calculation to a employee """
    template_name = "bonuses_list.html"

    def dispatch(self, request, *args, **kwargs):
        employee = Employee.objects.get(id=self.kwargs['employee_id'])
        if employee.is_subordinate() or request.user.groups.filter(name='Бухгалтери').exists():
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
        context_deal = context_deal_render(deal)

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
            generate_pdf(deal.customer.deal_template,
                         context_deal_render(deal),
                         Deal,
                         deal.pk
                         )
            return redirect(reverse('deal_update', args=[deal.pk]))
        except Deal.DoesNotExist:
            return HttpResponse('Deal object does not exist')


@method_decorator(login_required, name='dispatch')
class ActRender(TemplateView):
    """ View for rendering a deal """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        act = ActOfAcceptance.objects.get(id=self.kwargs['act_id'])
        context_act = context_act_render(act)
        return {**context, **context_act}

    def render_to_response(self, context):
        template = context['act'].deal.customer.act_template

        if template:
            return HttpResponse(template.render(context))
        else:
            return HttpResponse('HTML template does not exist for this customer')


@method_decorator(login_required, name='dispatch')
class ActGeneratePDF(View):
    """ Generating PDF copy for Deal """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        try:
            act = ActOfAcceptance.objects.get(pk=kwargs['act_id'])
            generate_pdf(act.deal.customer.act_template,
                         context_act_render(act),
                         ActOfAcceptance,
                         act.pk
                         )
            return redirect(reverse('deal_update', args=[act.deal.pk]))
        except ActOfAcceptance.DoesNotExist:
            return HttpResponse('Act object does not exist')


@method_decorator(login_required, name='dispatch')
class InvoiceRender(TemplateView):
    """ View for rendering a Invoice """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = Payment.objects.get(id=self.kwargs['payment_id'])
        context_act = context_invoice_render(payment)
        return {**context, **context_act}

    def render_to_response(self, context):
        template = context['invoice'].deal.customer.invoice_template

        if template:
            return HttpResponse(template.render(context))
        else:
            return HttpResponse('HTML template does not exist for this customer')


@method_decorator(login_required, name='dispatch')
class InvoiceGeneratePDF(View):
    """ Generating PDF copy for Invoice """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        try:
            payment = Payment.objects.get(pk=kwargs['payment_id'])
            generate_pdf(payment.deal.customer.invoice_template,
                         context_invoice_render(payment),
                         Payment,
                         payment.pk
                         )
            return redirect(reverse('deal_update', args=[payment.deal.pk]))
        except ActOfAcceptance.DoesNotExist:
            return HttpResponse('Act object does not exist')
