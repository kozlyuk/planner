# Generated by Django 3.2.18 on 2023-04-18 16:01

from django.db import migrations, models
import planner.formatChecker
import planner.models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0088_alter_order_pay_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='bank_requisites',
            field=models.TextField(blank=True, verbose_name='Банківські реквізити'),
        ),
        migrations.AddField(
            model_name='customer',
            name='bank_requisites',
            field=models.TextField(blank=True, verbose_name='Банківські реквізити'),
        ),
        migrations.AddField(
            model_name='payment',
            name='invoice_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата рахунку'),
        ),
        migrations.AddField(
            model_name='payment',
            name='invoice_number',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Номер рахунку'),
        ),
        migrations.AddField(
            model_name='payment',
            name='pdf_copy',
            field=planner.formatChecker.ContentTypeRestrictedFileField(blank=True, null=True, upload_to=planner.models.user_directory_path, verbose_name='Рахунок'),
        ),
    ]