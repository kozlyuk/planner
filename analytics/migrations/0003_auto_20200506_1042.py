# Generated by Django 2.2.10 on 2020-05-06 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_auto_20200505_1814'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonus',
            name='modified',
            field=models.DateField(auto_now=True),
        ),
        migrations.AddField(
            model_name='kpi',
            name='modified',
            field=models.DateField(auto_now=True),
        ),
    ]
