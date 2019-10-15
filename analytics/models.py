from django.db import models
from planner.models import Employee, Task


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
