# Generated by Django 3.2.18 on 2023-06-16 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0091_order_repeat'),
    ]

    operations = [
        migrations.AddField(
            model_name='construction',
            name='name_eng',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Construction'),
        ),
    ]
