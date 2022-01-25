from datetime import date
from enum import unique
from django.db import models

from planner.models import Employee
from html_templates.models import HTMLTemplate


class Kpi(models.Model):
    """ Model contains KPI """
    BonusItel = 'BI'
    BonusGKP = 'BG'
    BonusSIA = 'BS'
    Tasks = 'TA'
    Productivity = 'PR'
    KPI_CHOICES = (
        (BonusItel, 'Бонус Ітел-Ісервіс'),
        (BonusGKP, 'Бонус Галкомпроект'),
        (BonusSIA, 'Бонус Семенович'),
        (Tasks, 'Бонуси Загальні'),
        (Productivity, 'Продуктивність')
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
        return f"{self.employee.name} {self.get_name_display()}"


class Report(models.Model):
    """ Model contains Reports """
    CONTEXT_CHOICES = (
        ('receivables_context', 'Дебіторська заборгованість'),
        ('waiting_for_act_context', 'Чекають закриття актів'),
        ('payment_queue_context', 'Черга оплат'),
        ('overdue_payment_context', 'Протермінована опата'),
        ('overdue_execution_context', 'Протеріноване виконання'),
    )

    name = models.CharField('Назва звіту', max_length=50, unique=True)
    template = models.ForeignKey(HTMLTemplate, verbose_name='Шаблон', on_delete=models.PROTECT)
    context = models.CharField('Метод контексту', max_length=50, choices=CONTEXT_CHOICES)

    class Meta:
        verbose_name = 'Звіт'
        verbose_name_plural = 'Звіти'

    def __str__(self):
        return self.name
