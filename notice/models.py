
# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import models
from django.contrib.auth.models import User
from crum import get_current_user
from eventlog.models import log


class Event(models.Model):

    OneTime = 'OT'
    RepeatWeekly = 'RW'
    RepeatMonthly = 'RM'
    RepeatYearly = 'RY'
    REPEAT_CHOICES = (
        (OneTime, 'Одноразова подія'),
        (RepeatWeekly, 'Щотижнева подія'),
        (RepeatMonthly, 'Щомісячна подія'),
        (RepeatYearly, 'Щорічна подія')
    )
    date = models.DateField('Дата')
    next_date = models.DateField('Дата наступної події', blank=True, null=True)
    repeat = models.CharField('Періодичність', max_length=2, choices=REPEAT_CHOICES, default=OneTime)
    title = models.CharField('Назва події', max_length=100)
    description = models.TextField('Опис', blank=True)
    is_holiday = models.BooleanField('Вихідний день', default=False)
    creator = models.ForeignKey(User, verbose_name='Створив', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Подія'
        verbose_name_plural = 'Події'
        ordering = ['next_date']

    def save(self, *args, logging=True, **kwargs):
        self.next_date = self.next_repeat()
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Додана подія',
                    extra={"title": self.title})
            else:
                log(user=get_current_user(), action='Оновлена подія',
                    extra={"title": self.title})
        super(Event, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        log(user=get_current_user(), action='Видалена подія',
            extra={"title": self.title})
        super(Event, self).delete(*args, **kwargs)

    def __str__(self):
        return self.title

    def next_repeat(self):
        today = date.today()
        if self.repeat == self.OneTime:
            if self.date >= today:  # Target date already happened
                return self.date
            else:
                return None
        elif self.repeat == self.RepeatWeekly:
            return today + relativedelta(weekday=self.date.weekday())
        elif self.repeat == self.RepeatMonthly:
            delta = self.date.day - today.day
            if delta >= 0:
                return today + relativedelta(days=delta)
            else:
                return today + relativedelta(months=+1, days=delta)
        elif self.repeat == self.RepeatYearly:
            daydelta = self.date.day - today.day
            monthdelta = self.date.month - today.month
            yeardelta = today.year - self.date.year
            if monthdelta > 0 or (monthdelta == 0 and daydelta >= 0):
                return self.date + relativedelta(years=yeardelta)
            else:
                return self.date + relativedelta(years=yeardelta+1)

    @property
    def is_today(self):
        return self.next_date == date.today()

    def is_editable(self):
        user = get_current_user()
        if user.is_superuser or user == self.creator:
            return True
        else:
            return False


class News(models.Model):
    Organizational = 'OG'
    Leisure = 'LS'
    Production = 'PR'
    TYPE_CHOICES = (
        (Organizational, 'Організаційні'),
        (Leisure, 'Дозвілля'),
        (Production, 'Робочі'),
    )
    creator = models.ForeignKey(User, verbose_name='Створив', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    title = models.CharField('Назва новини', max_length=100)
    text = models.TextField('Новина')
    news_type = models.CharField('Тип новини', max_length=2, choices=TYPE_CHOICES, default=Production)
    actual_from = models.DateField('Актуальна з', blank=True, null=True)
    actual_to = models.DateField('Актуальна до', blank=True, null=True)

    class Meta:
        verbose_name = 'Новина'
        verbose_name_plural = 'Новини'
        ordering = ['-created']

    def save(self, *args, **kwargs):
        if not self.pk:
            self.creator = get_current_user()
        if not self.pk:
            log(user=get_current_user(), action='Додана новина',
                extra={"title": self.title})
        else:
            log(user=get_current_user(), action='Оновлена новина',
                extra={"title": self.title})
        super(News, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        log(user=get_current_user(), action='Видалена новина',
            extra={"title": self.title})
        super(News, self).delete(*args, **kwargs)

    def __str__(self):
        return self.title
