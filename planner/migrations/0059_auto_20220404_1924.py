# Generated by Django 2.2.27 on 2022-04-04 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0058_auto_20220404_1253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='head',
            field=models.ManyToManyField(blank=True, to='planner.Employee', verbose_name='Керівники'),
        ),
    ]
