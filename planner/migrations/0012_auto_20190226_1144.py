# Generated by Django 2.0.6 on 2019-02-26 09:44

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0011_auto_20190201_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='executors_bonus',
            field=models.PositiveSmallIntegerField(default=12, validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Бонус виконавців, %'),
        ),
        migrations.AlterField(
            model_name='project',
            name='owner_bonus',
            field=models.PositiveSmallIntegerField(default=6, validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Бонус керівника проекту, %'),
        ),
        migrations.AlterField(
            model_name='sending',
            name='comment',
            field=models.CharField(blank=True, max_length=255, verbose_name='Коментар'),
        ),
    ]
