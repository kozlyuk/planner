# Generated by Django 3.2.18 on 2023-07-03 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0094_execution_difficulty'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderpayment',
            name='doc_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Документ'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='doc_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Документ'),
        ),
    ]