from django.db import models

class HTMLTemplate(models.Model):

    Invoice = 'IN'
    Deal = 'DE'
    Act = 'AC'
    Report = 'RE'
    DOCUMENT_CHOICES = (
        (Invoice, 'Рахунок'),
        (Deal, 'Договір'),
        (Act, 'Акт'),
        (Report, 'Звіт')
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
