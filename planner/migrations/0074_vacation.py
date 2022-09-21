# Generated by Django 2.2.27 on 2022-08-02 18:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import planner.mixins


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('planner', '0073_remove_deal_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vacation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(verbose_name='Початок відпустки')),
                ('end_date', models.DateField(verbose_name='Кінець відпустки')),
                ('creation_date', models.DateField(auto_now_add=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vacation_creators', to=settings.AUTH_USER_MODEL, verbose_name='Створив')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='planner.Employee', verbose_name='Працівник')),
            ],
            options={
                'verbose_name': 'Відпустка',
                'verbose_name_plural': 'Відпустки',
                'ordering': ['-creation_date'],
                'unique_together': {('employee', 'start_date')},
            },
            bases=(planner.mixins.ModelDiffMixin, models.Model),
        ),
    ]