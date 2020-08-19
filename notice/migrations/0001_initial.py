# Generated by Django 2.2.10 on 2020-08-19 16:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('title', models.CharField(max_length=100, verbose_name='Назва новини')),
                ('text', models.TextField(verbose_name='Новина')),
                ('news_type', models.CharField(choices=[('OG', 'Організаційні'), ('LS', 'Дозвілля'), ('PR', 'Робочі')], default='PR', max_length=2, verbose_name='Тип новини')),
                ('actual_from', models.DateField(blank=True, null=True, verbose_name='Актуальна з')),
                ('actual_to', models.DateField(blank=True, null=True, verbose_name='Актуальна до')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Створив')),
            ],
            options={
                'verbose_name': 'Новина',
                'verbose_name_plural': 'Новини',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('date', models.DateField(verbose_name='Дата')),
                ('next_date', models.DateField(blank=True, null=True, verbose_name='Дата наступної події')),
                ('repeat', models.CharField(choices=[('OT', 'Одноразова подія'), ('RW', 'Щотижнева подія'), ('RM', 'Щомісячна подія'), ('RY', 'Щорічна подія')], default='OT', max_length=2, verbose_name='Періодичність')),
                ('title', models.CharField(max_length=100, verbose_name='Назва події')),
                ('description', models.TextField(blank=True, verbose_name='Опис')),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Створив')),
            ],
            options={
                'verbose_name': 'Подія',
                'verbose_name_plural': 'Події',
                'ordering': ['next_date'],
            },
        ),
    ]
