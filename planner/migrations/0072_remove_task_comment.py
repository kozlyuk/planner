# Generated by Django 2.2.27 on 2022-06-23 12:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0071_auto_20220609_1720'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='comment',
        ),
    ]
