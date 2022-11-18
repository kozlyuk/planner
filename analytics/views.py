from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView, View
from django.views.generic import FormView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse

from planner.models import Company, Customer

from .tasks import recalc_kpi, generate_pdf
from .models import Report, Chart
from .forms import ReportForm, ChartForm
from .context import context_report_render, context_chart_render


@method_decorator(login_required, name='dispatch')
class KpiRecalc(View):
    """ Recalc KPIs and Bonuses """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        period = None
        period__month = request.GET.get('period__month')
        period__year = request.GET.get('period__year')
        if period__month and period__year:
            period = datetime(year=int(period__year), month=int(period__month), day=1).date()

        recalc_kpi(period=period)

        return redirect(f"/admin/analytics/kpi/?{request.META['QUERY_STRING']}")


@method_decorator(login_required, name='dispatch')
class ReportView(FormView):
    """ Form for choosing reports """
    model = Report
    form_class = ReportForm
    template_name = 'report_form.html'
    success_url = reverse_lazy('report_render')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied


@method_decorator(login_required, name='dispatch')
class ReportRender(TemplateView):
    """ View for rendering a report """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = Report.objects.get(pk=self.request.GET.get('report'))
        context['company'] = Company.objects.get(pk=self.request.GET.get('company'))
        context['customer'] = Customer.objects.get(pk=self.request.GET.get('customer'))
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        context['from_date'] = datetime.strptime(from_date, '%Y-%m-%d') if from_date else None
        context['to_date'] = datetime.strptime(to_date, '%Y-%m-%d') if to_date else None
        context_report = context_report_render(context['report'], context['customer'], context['company'],
                                               context['from_date'], context['to_date']
                                               )
        return {**context, **context_report}

    def render_to_response(self, context):
        template = context['report'].template
        if template:
            if self.request.GET.get('generate_pdf'):
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="report.pdf"'
                pdf_file =  generate_pdf(template,
                                         context,
                                         )
                response.write(pdf_file)
                return response

            else:
                return HttpResponse(template.render(context))
        else:
            return HttpResponse('HTML template does not exist')

@method_decorator(login_required, name='dispatch')
class ChartView(FormView):
    """ Form for choosing reports """
    model = Chart
    form_class = ChartForm
    template_name = 'chart_form.html'
    success_url = reverse_lazy('chart_render')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied


@method_decorator(login_required, name='dispatch')
class ChartRender(TemplateView):
    """ View for rendering a chart """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser or request.user.groups.filter(name='Бухгалтери').exists():
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customers = self.request.GET.getlist('customer')
        context['chart'] = Chart.objects.get(pk=self.request.GET.get('chart'))
        context['customers'] = Customer.objects.filter(pk__in=customers)
        context['year'] = self.request.GET.get('year')
        context_report = context_chart_render(context['chart'], context['year'], context['customers'])
        return {**context, **context_report}

    def render_to_response(self, context):
        template = context['chart'].template
        if template:
            return HttpResponse(template.render(context))
        else:
            return HttpResponse('HTML template does not exist')
