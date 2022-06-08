# Generated by Django 2.2.27 on 2022-05-31 12:57

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0069_subtask_show_to_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='plan_reserve',
            field=models.DurationField(default=datetime.timedelta(seconds=28800), verbose_name='Запас плану'),
        ),
    ]