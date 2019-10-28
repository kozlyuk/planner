from django.db import models
from django.core.validators import MaxValueValidator

from planner.models import Employee


class Bonus(models.Model):
    employee = models.ForeignKey(Employee, verbose_name='Працівник', on_delete=models.CASCADE)
    value = models.DecimalField('Бонус, грн.', max_digits=8, decimal_places=2, default=0)
    created = models.DateField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Бонус'
        verbose_name_plural = 'Бонуси'
        ordering = ['-created']

    def __str__(self):
        return self.employee.name


class KpiName(models.Model):
    name = models.CharField('Назва показника', max_length=50, blank=True)

    class Meta:
        verbose_name = 'Показник ефективності'
        verbose_name_plural = 'Показники ефективності'

    def __str__(self):
        return self.name


class Kpi(models.Model):
    employee = models.ForeignKey(Employee, verbose_name='Працівник', on_delete=models.CASCADE)
    indicator = models.ForeignKey(KpiName, verbose_name='Показник', on_delete=models.CASCADE)
    value = models.PositiveSmallIntegerField('', validators=[MaxValueValidator(100)])
    created = models.DateField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'КПЕ'
        ordering = ['-created']

    def __str__(self):
        return self.employee.name + ' ' + self.indicator.name
