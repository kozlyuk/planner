# Generated by Django 2.2.4 on 2019-10-14 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0014_auto_20191003_1417'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='warning',
            field=models.CharField(blank=True, max_length=30, verbose_name='Попередження'),
        ),
    ]
