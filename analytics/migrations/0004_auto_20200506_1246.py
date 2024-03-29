# Generated by Django 2.2.10 on 2020-05-06 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_auto_20200506_1042'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='kpi',
            name='indicator',
        ),
        migrations.AddField(
            model_name='kpi',
            name='name',
            field=models.CharField(choices=[('BI', 'Бонус Ітел-Ісервіс'), ('BG', 'Бонус Галкомпроект')], default='BI', max_length=2, verbose_name='Показник ефективності'),
        ),
        migrations.AlterField(
            model_name='kpi',
            name='value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Значення'),
        ),
        migrations.DeleteModel(
            name='Bonus',
        ),
        migrations.DeleteModel(
            name='KpiName',
        ),
    ]
