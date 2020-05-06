from datetime import date
from django.db import models

from planner.models import Employee


class Kpi(models.Model):
    """ Model contains KPI """
    BonusItel = 'BI'
    BonusGKP = 'BG'
    KPI_CHOICES = (
        (BonusItel, 'Бонус Ітел-Ісервіс'),
        (BonusGKP, 'Бонус Галкомпроект')
    )
    employee = models.ForeignKey(Employee, verbose_name='Працівник', on_delete=models.CASCADE)
    name = models.CharField('Показник ефективності', max_length=2, choices=KPI_CHOICES, default=BonusItel)
    value = models.DecimalField('Значення', max_digits=8, decimal_places=2, default=0)
    period = models.DateField('Період розрахунку', default=date.today)
    modified = models.DateField(auto_now=True)

    class Meta:
        verbose_name = 'КПЕ'
        ordering = ['-period']

    def __str__(self):
        return f"{self.employee.name} {self.get_name_display}"
