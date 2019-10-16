# Generated by Django 2.2.5 on 2019-10-03 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0013_remove_contractor_project_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='deal',
            name='exec_status',
            field=models.CharField(choices=[('IW', 'В черзі'), ('IP', 'Виконується'), ('HD', 'Виконано'), ('ST', 'Надіслано')], default='IW', max_length=2, verbose_name='Статус виконання'),
        ),
        migrations.AddField(
            model_name='deal',
            name='warning',
            field=models.CharField(blank=True, max_length=30, verbose_name='Попередження'),
        ),
    ]
