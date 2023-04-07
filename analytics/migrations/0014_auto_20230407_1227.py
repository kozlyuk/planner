# Generated by Django 3.2.18 on 2023-04-07 12:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('analytics', '0013_alter_kpi_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='chart',
            name='content_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='chart',
            name='context',
            field=models.CharField(choices=[('fin_analysis_context', 'Фінансова аналітика'), ('customer_fin_analysis_context', 'Фінансова аналітика по замовнику'), ('income_structure_context', 'Структура доходів'), ('employee_productivity_context', 'Продуктивність працівників')], max_length=50, verbose_name='Метод контексту'),
        ),
    ]
