# Generated by Django 2.2.20 on 2022-02-10 11:36

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0049_company_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Назва робіт')),
                ('part', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Частка від проекту')),
                ('duration', models.DurationField(default=datetime.timedelta(seconds=28800), verbose_name='Тривалість виконання')),
                ('base', models.BooleanField(default=False, verbose_name='Базова')),
                ('project_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='planner.Project', verbose_name='Тип проекту')),
            ],
            options={
                'verbose_name': 'Підзадача',
                'verbose_name_plural': 'Підзадачі',
                'ordering': ['-project_type'],
                'unique_together': {('project_type', 'name')},
            },
        ),
        migrations.AddField(
            model_name='execution',
            name='subtask',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='planner.SubTask', verbose_name='Підзадача'),
        ),
    ]
