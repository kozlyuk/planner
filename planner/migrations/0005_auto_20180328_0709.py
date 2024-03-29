# Generated by Django 2.0 on 2018-03-28 04:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0004_auto_20180305_1653'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='employee',
            options={'ordering': ['name'], 'verbose_name': 'Працівник', 'verbose_name_plural': 'Працівники'},
        ),
        migrations.AlterField(
            model_name='task',
            name='exec_status',
            field=models.CharField(choices=[('IW', 'В черзі'), ('IP', 'Виконується'), ('HD', 'Виконано'), ('ST', 'Надіслано')], default='IW', max_length=2, verbose_name='Статус виконання'),
        ),
    ]
