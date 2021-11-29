from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .tasks import calc_bonuses, calc_kpi


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

        calc_bonuses(period=period)
        calc_kpi(period=period)

        return redirect(f"/admin/analytics/kpi/?{request.META['QUERY_STRING']}")
