# Generated by Django 2.2.8 on 2019-12-26 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0021_auto_20191211_2102'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='need_project_code',
            field=models.BooleanField(default=True, verbose_name='Потрібен шифр проекту'),
        ),
        migrations.AlterField(
            model_name='task',
            name='manual_warning',
            field=models.CharField(blank=True, max_length=30, verbose_name='Примітка'),
        ),
    ]
