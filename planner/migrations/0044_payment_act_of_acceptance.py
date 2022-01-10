# Generated by Django 2.2.20 on 2021-12-15 10:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0043_auto_20211201_1505'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='act_of_acceptance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='planner.ActOfAcceptance', verbose_name='Акт виконаних робіт'),
        ),
    ]