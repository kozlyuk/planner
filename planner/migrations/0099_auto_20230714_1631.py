# Generated by Django 3.2.18 on 2023-07-14 16:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0098_plan'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='execution',
            name='prev_exec_status',
        ),
        migrations.AlterField(
            model_name='execution',
            name='exec_status',
            field=models.CharField(choices=[('IW', 'В черзі'), ('IP', 'Виконується'), ('OH', 'Призупинено'), ('OC', 'На перевірці'), ('CR', 'На коригуванні'), ('HD', 'Виконано')], default='IW', max_length=2, verbose_name='Статус виконання'),
        ),
    ]
