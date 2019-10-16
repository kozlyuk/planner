# Generated by Django 2.0.6 on 2018-06-14 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0005_auto_20180328_0709'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'ordering': ['-price_code'], 'verbose_name': 'Вид робіт', 'verbose_name_plural': 'Види робіт'},
        ),
        migrations.AlterField(
            model_name='company',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='Назва'),
        ),
        migrations.AlterField(
            model_name='contractor',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='Назва'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='Назва'),
        ),
        migrations.AlterField(
            model_name='receiver',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='Отримувач'),
        ),
    ]
