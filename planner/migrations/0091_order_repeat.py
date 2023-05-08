# Generated by Django 3.2.18 on 2023-05-05 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0090_auto_20230427_1725'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='repeat',
            field=models.CharField(choices=[('OT', 'Одноразовий платіж'), ('RM', 'Щомісячний платіж')], default='OT', max_length=2, verbose_name='Періодичність'),
        ),
    ]
