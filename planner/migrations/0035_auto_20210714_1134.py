# Generated by Django 2.2.20 on 2021-07-14 11:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('html_templates', '0001_initial'),
        ('planner', '0034_move_acts_and_payments'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='act_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='customers_acts', to='html_templates.HTMLTemplate', verbose_name='Шаблон акту'),
        ),
        migrations.AddField(
            model_name='customer',
            name='deal_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='customers_deals', to='html_templates.HTMLTemplate', verbose_name='Шаблон договору'),
        ),
        migrations.AddField(
            model_name='customer',
            name='invoice_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='customers_invoices', to='html_templates.HTMLTemplate', verbose_name='Шаблон рахунку'),
        ),
        migrations.AddField(
            model_name='customer',
            name='report_template',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='customers_reports', to='html_templates.HTMLTemplate', verbose_name='Шаблон звіту'),
        ),
    ]
