# Generated by Django 3.2.18 on 2023-07-12 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0096_alter_execution_difficulty'),
    ]

    operations = [
        migrations.AddField(
            model_name='subtask',
            name='difficulty',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=3, verbose_name='Коефіцієнт складності'),
        ),
    ]