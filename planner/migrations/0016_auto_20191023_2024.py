# Generated by Django 2.2.4 on 2019-10-23 17:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0015_task_warning'),
    ]

    operations = [
        migrations.AddField(
            model_name='deal',
            name='manual_warning',
            field=models.CharField(blank=True, max_length=30, verbose_name='Попередження'),
        ),
        migrations.AddField(
            model_name='execution',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Початок виконання'),
        ),
        migrations.AddField(
            model_name='task',
            name='manual_warning',
            field=models.CharField(blank=True, max_length=30, verbose_name='Попередження'),
        ),
        migrations.AlterField(
            model_name='execution',
            name='finish_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Кінець виконання'),
        ),
        migrations.AlterField(
            model_name='sending',
            name='receiver',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='planner.Receiver', verbose_name='Отримувач проекту'),
        ),
    ]
