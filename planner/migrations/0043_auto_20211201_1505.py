# Generated by Django 2.2.20 on 2021-12-01 15:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0042_auto_20211126_1657'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deal',
            name='act_date',
        ),
        migrations.RemoveField(
            model_name='deal',
            name='act_value',
        ),
        migrations.RemoveField(
            model_name='deal',
            name='advance',
        ),
        migrations.RemoveField(
            model_name='deal',
            name='pay_date',
        ),
    ]
