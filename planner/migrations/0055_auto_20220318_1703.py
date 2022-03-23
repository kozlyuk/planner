# Generated by Django 2.2.20 on 2022-03-18 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0054_auto_20220214_1526'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'verbose_name': 'Замовлення', 'verbose_name_plural': 'Замовлення'},
        ),
        migrations.AlterField(
            model_name='execution',
            name='finish_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Кінець виконання'),
        ),
        migrations.AlterField(
            model_name='execution',
            name='planned_finish',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Планове закінчення'),
        ),
        migrations.AlterField(
            model_name='execution',
            name='planned_start',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Плановий початок'),
        ),
        migrations.AlterField(
            model_name='execution',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Початок виконання'),
        ),
    ]
