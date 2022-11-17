from django.db import models
from django.template import Context, Template

class HTMLTemplate(models.Model):

    Invoice = 'IN'
    Deal = 'DE'
    Act = 'AC'
    Report = 'RE'
    Chart = 'CH'
    DOCUMENT_CHOICES = (
        (Invoice, 'Рахунок'),
        (Deal, 'Договір'),
        (Act, 'Акт'),
        (Report, 'Звіт'),
        (Chart, 'Діаграма'),
    )

    name = models.CharField('Назва шаблону', max_length=50, unique=True)
    document_type = models.CharField('Тип документу', max_length=2, choices=DOCUMENT_CHOICES, default=Deal)
    html_template = models.TextField("Шаблон HTML")
    html_context = models.CharField("Контекст шаблону", max_length=255, blank=True)

    class Meta:
        verbose_name = 'Шаблон'
        verbose_name_plural = 'Шаблони'
        ordering = ['name']

    def __str__(self):
        return self.name

    def render(self, context):
        """
        Template rendering, variables substitution.
        """

        tpl = Template(self.html_template)
        return tpl.render(Context(context))
