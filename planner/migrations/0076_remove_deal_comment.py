# Generated by Django 2.2.27 on 2022-08-09 16:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0075_deal_comment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deal',
            name='comment',
        ),
    ]
