# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from pandas.tseries.offsets import BDay
from django.core.validators import MaxValueValidator
from django.db.models import Q, Sum
from django.conf.locale.uk import formats as uk_formats
from crum import get_current_user
from .formatChecker import ContentTypeRestrictedFileField
from stdimage.models import StdImageField
from eventlog.models import log
from django.db.models.signals import post_save
from django.dispatch import receiver


date_format = uk_formats.DATE_INPUT_FORMATS[0]


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/projects/user_<id>/Year/Month/<filename>
    return 'projects/user_{0}/{1}/{2}/{3}'\
        .format(get_current_user().id, datetime.now().year, datetime.now().month, filename)


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    name = models.CharField('ПІБ', max_length=50, unique=True)
    position = models.CharField('Посада', max_length=50)
    head = models.ForeignKey('self', verbose_name='Кервіник', on_delete=models.PROTECT)
    phone = models.CharField('Телефон', max_length=13, blank=True)
    mobile_phone = models.CharField('Мобільний телефон', max_length=13, blank=True)
    avatar = StdImageField('Фото', upload_to='users/avatars', default='users/avatars/no_image.jpg', variations={
                           'large': (400, 400, True),
                           'thumbnail': (100, 100, True),
                           })
    birthday = models.DateField('День народження', blank=True, null=True)
    salary = models.DecimalField('Заробітна плата, грн.', max_digits=8, decimal_places=2, default=0)
    vacation_count = models.PositiveSmallIntegerField('Кількість днів відпустки', blank=True, null=True,
                                                      validators=[MaxValueValidator(100)])
    vacation_date = models.DateField('Дата нарахування відпустки', blank=True, null=True)

    class Meta:
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'
        ordering = ['name']

    def __str__(self):
        return self.name

    def owner_count(self):
        active = 0
        overdue = 0
        for task in self.task_set.exclude(exec_status=Task.Sent):
            active += 1
            if task.overdue_status().startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    owner_count.short_description = 'Керівник проектів'

    def task_count(self):
        active = 0
        overdue = 0
        for task in self.tasks.exclude(exec_status=Task.Sent):
            active += 1
            if task.overdue_status().startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    task_count.short_description = 'Виконавець в проектах'

    def inttask_count(self):
        active = self.inttask_set.exclude(exec_status=IntTask.Done).count()
        overdue = self.inttask_set.exclude(exec_status=IntTask.Done)\
                                  .exclude(planned_finish__gte=date.today()).count()
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    inttask_count.short_description = 'Завдання'

    @staticmethod
    def date_delta(delta):
        month = datetime.now().month + delta
        year = datetime.now().year
        if month < 1:
            month += 12
            year += -1
        return month, year

    def exec_bonuses(self, delta):
        bonuses = 0
        month, year = self.date_delta(delta)

        executions = self.execution_set.filter(Q(task__exec_status=Task.Done) |
                                               Q(task__exec_status=Task.Sent),
                                               part__gt=0,
                                               task__actual_finish__month=month,
                                               task__actual_finish__year=year)
        for query in executions:
            bonuses += query.task.exec_bonus(query.part)

        return round(bonuses, 2)
        # executor bonuses

    def owner_bonuses(self, delta):
        bonuses = 0
        month, year = self.date_delta(delta)

        tasks = self.task_set.filter(exec_status=Task.Sent,
                                     actual_finish__month=month,
                                     actual_finish__year=year)
        for query in tasks:
            bonuses += query.owner_bonus()

        return round(bonuses, 2)
        # owner bonuses

    def inttask_bonuses(self, delta):
        bonuses = 0
        month, year = self.date_delta(delta)

        inttasks = self.inttask_set.filter(exec_status=IntTask.Done,
                                           actual_finish__month=month,
                                           actual_finish__year=year)
        for query in inttasks:
            bonuses += query.bonus

        return round(bonuses, 2)
        # inttask bonuses

    def total_bonuses(self, delta):
        return self.exec_bonuses(delta) + self.owner_bonuses(delta) + self.inttask_bonuses(delta)
        # total bonuses


    def total_bonuses_cm(self):
        return self.total_bonuses(0)
    total_bonuses_cm.short_description = 'Бонуси {}.{}'.format(datetime.now().month, datetime.now().year)

    def total_bonuses_pm(self):
        return self.total_bonuses(-1)
    total_bonuses_pm.short_description = 'Бонуси {}.{}'\
        .format(datetime.now().month -1 if datetime.now().month >1 else datetime.now().month + 11,
                datetime.now().year if datetime.now().month >1 else datetime.now().year - 1)

    def total_bonuses_ppm(self):
        return self.total_bonuses(-2)
    total_bonuses_ppm.short_description = 'Бонуси {}.{}'\
        .format(datetime.now().month -2 if datetime.now().month >2 else datetime.now().month + 10,
                datetime.now().year if datetime.now().month >2 else datetime.now().year - 1)


class Customer(models.Model):
    ACT_TEMPLATE_CHOICES = (
        ('gks', 'Шаблон ГКС'),
        ('msz', 'Шаблон МС'),
    )
    name = models.CharField('Назва', max_length=50, unique=True)
    contact_person = models.CharField('Контактна особа', max_length=50)
    phone = models.CharField('Телефон', max_length=13)
    email = models.EmailField('Email')
    requisites = models.TextField('Реквізити', blank=True)
    debtor_term = models.PositiveSmallIntegerField('Термін післяоплати', blank=True, null=True)
    act_template = models.CharField('Шаблон акту', max_length=3, choices=ACT_TEMPLATE_CHOICES, default='gks')

    class Meta:
        verbose_name = 'Замовник'
        verbose_name_plural = 'Замовники'

    def __str__(self):
        return self.name

    def debit_calc(self):
        total = 0
        for deal in self.deal_set.all():
            if deal.pay_status == Deal.NotPaid:
                total += deal.act_value
            if deal.pay_status == Deal.AdvancePaid and deal.act_value > deal.advance:
                total += deal.act_value - deal.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    debit_calc.short_description = 'Дебіторська заборгованість {}'.format(datetime.now().year)

    def credit_calc(self):
        total = 0
        for deal in self.deal_set.all():
            if deal.pay_status == Deal.AdvancePaid and deal.act_value < deal.advance:
                total += deal.advance - deal.act_value
            if deal.pay_status == Deal.PaidUp and deal.act_value < deal.value:
                total += deal.value - deal.act_value
        return u'{0:,}'.format(total).replace(u',', u' ')
    credit_calc.short_description = 'Авансові платежі'

    def completed_calc(self):
        total = 0
        for deal in self.deal_set.filter(act_date__year=datetime.now().year):
            if deal.pay_status == Deal.PaidUp:
                total += deal.act_value
            if deal.pay_status == Deal.AdvancePaid and deal.act_value >= deal.advance:
                total += deal.advance
            if deal.pay_status == Deal.AdvancePaid and deal.act_value < deal.advance:
                total += deal.act_value
        return u'{0:,}'.format(total).replace(u',', u' ')
    completed_calc.short_description = 'Виконано та оплачено {}'.format(datetime.now().year)

    def expect_calc(self):
        total = 0
        for deal in self.deal_set.all():
            if deal.pay_status == Deal.NotPaid and deal.act_value < deal.value:
                total += deal.value - deal.act_value
            if deal.pay_status == Deal.AdvancePaid and deal.act_value <= deal.advance:
                total += deal.value - deal.advance
            if deal.pay_status == Deal.AdvancePaid and deal.act_value > deal.advance:
                total += deal.value - deal.act_value
        return u'{0:,}'.format(total).replace(u',', u' ')
    expect_calc.short_description = 'Не виконано та не оплачено'


class Project(models.Model):
    project_type = models.CharField('Вид робіт', max_length=100)
    customer = models.ForeignKey(Customer, verbose_name='Замовник', on_delete=models.PROTECT)
    price_code = models.CharField('Пункт кошторису', max_length=8, unique=True)
    price = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    net_price_rate = models.PositiveSmallIntegerField('Вартість після вхідних витрат, %',
                                                      validators=[MaxValueValidator(100)], default=75)
    owner_bonus = models.PositiveSmallIntegerField('Бонус керівника проекту, %',
                                                      validators=[MaxValueValidator(100)], default=5)
    executors_bonus = models.PositiveSmallIntegerField('Бонус виконавців, %',
                                                      validators=[MaxValueValidator(100)], default=10)
    copies_count = models.PositiveSmallIntegerField('Кількість примірників',default=0,
                                                    validators=[MaxValueValidator(10)])
    description = models.TextField('Опис', blank=True)
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Вид робіт'
        verbose_name_plural = 'Види робіт'
        ordering = ['-price_code']

    def __str__(self):
        return self.price_code + ' ' + self.project_type + ' ' + self.customer.name

    def net_price(self):
        net_price = self.price * self.net_price_rate / 100
        return round(net_price, 2)
    net_price.short_description = 'Вартість після вхідних витрат'

    def turnover_calc(self):
        total = 0
        for task in self.task_set.filter(actual_finish__year=datetime.now().year):
            total += task.project_type.price
        return u'{0:,}'.format(total).replace(u',', u' ')
    turnover_calc.short_description = 'Оборот по пункту'


class Company(models.Model):
    TAXATION_CHOICES = (
        ('wvat', 'З ПДВ'),
        ('wovat', 'Без ПДВ'),
    )
    name = models.CharField('Назва', max_length=50, unique=True)
    chief = models.ForeignKey(Employee, verbose_name='Керівник', on_delete=models.PROTECT)
    taxation = models.CharField('Система оподаткування', max_length=5, choices=TAXATION_CHOICES, default='wvat')
    requisites = models.TextField('Реквізити', blank=True)

    class Meta:
        verbose_name = 'Компанія'
        verbose_name_plural = 'Компанії'

    def __str__(self):
        return self.name

    def turnover_calc(self):
        total = 0
        for deal in self.deal_set.filter(act_date__year=datetime.now().year):
            total += deal.act_value
        return u'{0:,}'.format(total).replace(u',', u' ')
    turnover_calc.short_description = 'Оборот {}'.format(datetime.now().year)

    def costs_calc(self):
        total = 0
        for deal in self.deal_set.filter(act_date__year=datetime.now().year):
            total += deal.costs_calc()
        return u'{0:,}'.format(total).replace(u',', u' ')
    costs_calc.short_description = 'Витрати {}'.format(datetime.now().year)

    def bonuses_calc(self):
        total = 0
        for deal in self.deal_set.filter(act_date__year=datetime.now().year):
            total += deal.bonuses_calc()
        return u'{0:,}'.format(total).replace(u',', u' ')
    bonuses_calc.short_description = 'Бонуси {}'.format(datetime.now().year)


class Contractor(models.Model):
    name = models.CharField('Назва', max_length=50, unique=True)
    contact_person = models.CharField('Контактна особа', max_length=50)
    phone = models.CharField('Телефон', max_length=13)
    email = models.EmailField('Email')
    requisites = models.TextField('Реквізити', blank=True)
    project_types = models.ManyToManyField(Project, verbose_name='Види робіт', blank=True)
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Підрярник'
        verbose_name_plural = 'Підрядники'

    def __str__(self):
        return self.name

    def advance_calc(self):
        total = 0
        for order in self.order_set.exclude(task__exec_status=Task.Done):
            if order.pay_status == Order.AdvancePaid:
                total += order.advance
            if order.pay_status == Order.PaidUp:
                total += order.value
        return u'{0:,}'.format(total).replace(u',', u' ')
    advance_calc.short_description = 'Авансові платежі'

    def credit_calc(self):
        total = 0
        for order in self.order_set.filter(task__exec_status=Task.Done):
            if order.pay_status == Order.NotPaid:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.value - order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    credit_calc.short_description = 'Кредиторська заборгованість'

    def expect_calc(self):
        total = 0
        for order in self.order_set.exclude(task__exec_status=Task.Done):
            if order.pay_status == Order.PaidUp:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.value - order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    expect_calc.short_description = 'Не виконано та не оплачено'

    def completed_calc(self):
        total = 0
        for order in self.order_set.filter(task__exec_status=Task.Done,
                                           pay_date__year=datetime.now().year):
            if order.pay_status == Order.PaidUp:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    completed_calc.short_description = 'Виконано та оплачено'


class Deal(models.Model):
    NotPaid = 'NP'
    AdvancePaid = 'AP'
    PaidUp = 'PU'
    PAYMENT_STATUS_CHOICES = (
        (NotPaid, 'Не оплачений'),
        (AdvancePaid, 'Оплачений аванс'),
        (PaidUp, 'Оплачений')
        )
    NotIssued = 'NI'
    PartlyIssued = 'PI'
    Issued = 'IS'
    ACT_STATUS_CHOICES = (
        (NotIssued, 'Не виписаний'),
        (PartlyIssued, 'Виписаний частково'),
        (Issued, 'Виписаний')
        )
    number = models.CharField('Номер договору', max_length=30)
    date = models.DateField('Дата договору', default=now)
    customer = models.ForeignKey(Customer, verbose_name='Замовник', on_delete=models.PROTECT)
    company = models.ForeignKey(Company, verbose_name='Компанія', on_delete=models.PROTECT)
    value = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    value_correction = models.DecimalField('Коригування вартості робіт, грн.', max_digits=8, decimal_places=2, default=0)
    advance = models.DecimalField('Аванс, грн.', max_digits=8, decimal_places=2, default=0)
    pay_status = models.CharField('Статус оплати', max_length=2, choices=PAYMENT_STATUS_CHOICES, default=NotPaid)
    pay_date = models.DateField('Дата оплати', blank=True, null=True)
    expire_date = models.DateField('Дата закінчення договору')
    act_status = models.CharField('Акт виконаних робіт', max_length=2, choices=ACT_STATUS_CHOICES, default=NotIssued)
    act_date = models.DateField('Дата акту виконаних робіт', blank=True, null=True)
    act_value = models.DecimalField('Сума акту виконаних робіт, грн.', max_digits=8, decimal_places=2, default=0)
    comment = models.TextField('Коментар', blank=True)
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='deal_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)
    pdf_copy = ContentTypeRestrictedFileField('Електронний примірник', upload_to=user_directory_path,
                                              content_types=['application/pdf',
                                                             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                                              max_upload_size=26214400,
                                              blank=True, null=True)

    class Meta:
        unique_together = ('number', 'customer')
        verbose_name = 'Договір'
        verbose_name_plural = 'Договори'
        ordering = ['-creation_date', 'customer', '-number']

    def __str__(self):
        return self.number + ' ' + self.customer.name

    def save(self, logging=True, *args, **kwargs):
        title = self.number
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Доданий договір', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлений договір', extra={"title": title})
        super(Deal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = self.number
        log(user=get_current_user(), action='Видалений договір', extra={"title": title})
        super(Deal, self).delete(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(Deal, self).__init__(*args, **kwargs)
        self.__customer__ = None

    def svalue(self):
        return u'{0:,}'.format(self.value).replace(u',', u' ')
    svalue.short_description = 'Вартість робіт, грн.'

    def exec_status(self):
        queryset = self.task_set.all()
        for task in queryset:
            if task.exec_status == Task.ToDo:
                return 'В черзі'
        for task in queryset:
            if task.exec_status == Task.InProgress:
                return 'Виконується'
        for task in queryset:
            if task.exec_status == Task.Done:
                return 'Виконано'
        for task in queryset:
            if task.exec_status == Task.Sent:
                return 'Надіслано'
        return 'Відсутні проекти'
    exec_status.short_description = 'Статус виконання'

    def overdue_status(self):
        if 'загальний' in self.number:
            return ''
        if self.exec_status() == 'Надіслано':
            value_calc = self.value_calc() + self.value_correction
            if self.value > 0 and self.value != value_calc:
                return 'Вартість по роботам %s' % value_calc
            if self.act_status == self.NotIssued or self.act_status == self.PartlyIssued:
                return 'Очікує закриття акту'
            if self.pay_status != self.PaidUp and self.pay_date:
                return 'Оплата %s' % self.pay_date.strftime(date_format)
            return ''
        elif self.expire_date < date.today():
            return 'Протерміновано %s' % self.expire_date.strftime(date_format)
        elif self.expire_date - timedelta(days=7) <= date.today():
            return 'Закінчується %s' % self.expire_date.strftime(date_format)
        return ''

    def bonuses_calc(self):                                          # total deal's bonuses
        total = 0
        for task in self.task_set.all():
            total += task.total_bonus()
        return round(total, 2)
    bonuses_calc.short_description = 'Бонуси по договору, грн.'

    def value_calc(self):                                            # total deal's price
        total = 0
        for task in self.task_set.all():
            price = task.project_type.price
            if self.company.taxation == 'wovat':
                price = price / 6 * 5
            total += price
        return round(total, 2)
    value_calc.short_description = 'Вартість договору по роботам, грн.'

    def costs_calc(self):                                            # total deal's costs
        total = 0
        for task in self.task_set.all():
            total += task.costs_total()
        return round(total, 2)
    costs_calc.short_description = 'Витрати по договору, грн.'

    def pay_date_calc(self):                                            # total deal's costs
        if self.customer.debtor_term:
            if self.act_date:
                pay_date = self.act_date + BDay(self.customer.debtor_term)
                return pay_date.strftime(date_format)
            elif self.expire_date:
                pay_date = self.expire_date + BDay(self.customer.debtor_term)
                return pay_date.strftime(date_format)
        return
    pay_date_calc.short_description = 'Дата оплати, грн.'


class Receiver(models.Model):
    customer = models.ForeignKey(Customer, verbose_name='Замовник', on_delete=models.PROTECT)
    name = models.CharField('Отримувач', max_length=50, unique=True)
    address = models.CharField('Адреса', max_length=255)
    contact_person = models.CharField('Контактна особа', max_length=50)
    phone = models.CharField('Телефон', max_length=13)
    comment = models.TextField('Коментар', blank=True)

    class Meta:
        verbose_name = 'Адресат'
        verbose_name_plural = 'Адресати'

    def __str__(self):
        return self.name


class Task(models.Model):
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    Sent = 'ST'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано'),
        (Sent, 'Надіслано')
    )
    object_code = models.CharField('Шифр об’єкту', max_length=30)
    object_address = models.CharField('Адреса об’єкту', max_length=255)
    project_type = models.ForeignKey(Project, verbose_name='Тип проекту', on_delete=models.PROTECT)
    project_code = models.CharField('Шифр проекту', max_length=30, blank=True)
    deal = models.ForeignKey(Deal, verbose_name='Договір', on_delete=models.PROTECT)
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    owner = models.ForeignKey(Employee, verbose_name='Керівник проекту', on_delete=models.PROTECT)
    executors = models.ManyToManyField(Employee, through='Execution', related_name='tasks',
                                       verbose_name='Виконавці', blank=True)
    costs = models.ManyToManyField(Contractor, through='Order', related_name='tasks',
                                   verbose_name='Підрядники', blank=True)
    planned_start = models.DateField('Плановий початок', blank=True, null=True)
    planned_finish = models.DateField('Планове закінчення', blank=True, null=True)
    actual_start = models.DateField('Фактичний початок', blank=True, null=True)
    actual_finish = models.DateField('Фактичне закінчення', blank=True, null=True)
    tc_received = models.DateField('Дата отримання ТЗ', blank=True, null=True)
    tc_upload = ContentTypeRestrictedFileField('Технічне завдання', upload_to=user_directory_path,
                                               content_types=['application/pdf', ], max_upload_size=10485760,
                                               blank=True, null=True)
    receivers = models.ManyToManyField(Receiver, through='Sending', verbose_name='Отримувачі проекту')
    comment = models.TextField('Коментар', blank=True)
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='task_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)
    pdf_copy = ContentTypeRestrictedFileField('Електронний примірник', upload_to=user_directory_path,
                                              content_types=['application/pdf',
                                                             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                                              max_upload_size=26214400,
                                              blank=True, null=True)

    class Meta:
        unique_together = ('object_code', 'project_type', 'deal')
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекти'
        ordering = ['-creation_date', '-deal', 'object_code']

    def __str__(self):
        return self.object_code + ' ' + self.project_type.__str__()

    def save(self, logging=True, *args, **kwargs):
        title = self.object_code + ' ' + self.project_type.price_code
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Доданий проект', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлений проект', extra={"title": title})
        super(Task, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = self.object_code + ' ' + self.project_type.price_code
        log(user=get_current_user(), action='Видалений проект', extra={"title": title})
        super(Task, self).delete(*args, **kwargs)

    def execution_status(self):
        queryset = self.execution_set.all()
        for execution in queryset:
            if execution.exec_status == Execution.ToDo:
                return 'В черзі'
        for execution in queryset:
            if execution.exec_status == Execution.InProgress:
                return 'Виконується'
        for execution in queryset:
            if execution.exec_status == Execution.Done:
                return 'Виконано'
        return 'Відсутні виконавці'
    execution_status.short_description = 'Статус виконання частин проекту'

    def sending_status(self):
        if self.receivers.all():
            if self.receivers.all().aggregate(Sum('sending__copies_count')).get('sending__copies_count__sum') \
                    < self.project_type.copies_count:
                return 'Не всі відправки'
        elif self.project_type.copies_count > 0:
            return 'Не надіслано'
        return 'Надіслано'
    # displays task sending warnings

    def overdue_status(self):
        if self.exec_status == self.Done:
            if self.sending_status() != 'Надіслано':
                return self.sending_status()
        if self.exec_status in [self.Sent, self.Done] and self.actual_finish:
            return 'Виконано %s' % self.actual_finish.strftime(date_format)
        if self.execution_status() == 'Виконано':
            return 'Очікує на перевірку'
        if self.planned_finish:
            if self.planned_finish < date.today():
                return 'Протерміновано %s' % self.planned_finish.strftime(date_format)
            elif self.planned_finish - timedelta(days=7) <= date.today():
                return 'Завершується %s' % self.planned_finish.strftime(date_format)
            else:
                return 'Завершити до %s' % self.planned_finish.strftime(date_format)
        if self.deal.expire_date < date.today():
            return 'Протерміновано %s' % self.deal.expire_date.strftime(date_format)
        if self.deal.expire_date - timedelta(days=7) <= date.today():
            return 'Завершується %s' % self.deal.expire_date.strftime(date_format)
        return 'Завершити до %s' % self.deal.expire_date.strftime(date_format)
    # displays task overdue status

    def is_active(self):
        if not self.actual_finish:
            return True
        if self.deal.act_status == Deal.Issued:
            return False
        if self.actual_finish.month >= (datetime.now().month + 12*(datetime.now().year-self.actual_finish.year)-1):
            if self.actual_finish.month == datetime.now().month:
                return True
            if datetime.now().day < 6:
                return True
        return False
    # try if task edit period is not expired

    def is_viewable(self):
        user = get_current_user()
        if user.is_superuser:
            return True
        elif user == self.owner.user or self.executors.filter(user=user).exists() \
                or self.executors.filter(head__user=user).exists():
            return True
        else:
            return False
    # try if user has a permitting to view the task

    def is_editable(self):
        user = get_current_user()
        if user.is_superuser:
            return True
        elif self.is_active() and user == self.owner.user:
            return True
        elif self.deal.act_status != Deal.Issued and user.groups.filter(name='Бухгалтери').exists():
            return True
        else:
            return False
    # try if user has a permitting to edit the task

    def is_markable(self):
        user = get_current_user()
        if user.is_superuser:
            return True
        elif self.is_active():
            if user == self.owner.user or self.executors.filter(user=user).exists():
                return True
        else:
            return False
    # try if user has a permitting to mark execution of the task

    def costs_total(self):
        costs = self.costs.all().aggregate(Sum('order__value')).get('order__value__sum')
        return costs if costs is not None else 0
    # total task's costs

    def exec_part(self):
        part = self.executors.all().aggregate(Sum('execution__part')).get('execution__part__sum')
        return part if part is not None else 0
    # executors part

    def outsourcing_part(self):
        part = self.executors.filter(user__username__startswith='outsourcing').aggregate(Sum('execution__part'))\
            .get('execution__part__sum')
        return part if part is not None else 0
    # outsourcing part

    def owner_part(self):
        if self.project_type.owner_bonus > 0:
            part = int(100 + (100 - self.exec_part())*self.project_type.executors_bonus/self.project_type.owner_bonus)
        else:
            part = 0
        return part
    # owner part

    def owner_bonus(self):
        return (self.project_type.net_price() - self.costs_total()) * self.owner_part()\
               * self.project_type.owner_bonus / 10000
    # owner's bonus

    def exec_bonus(self, part):
        return self.project_type.net_price() * part * self.project_type.executors_bonus / 10000
    # executor's bonus

    def executors_bonus(self):
        return self.exec_bonus(self.exec_part())
    # executors bonuses

    def total_bonus(self):
        return self.exec_bonus(self.exec_part() - self.outsourcing_part()) + self.owner_bonus()
    # total bonus


@receiver(post_save, sender=Task, dispatch_uid="update_subtasks_status")
def update_subtasks(sender, instance, **kwargs):
    if instance.exec_status in [Task.Done, Task.Sent]:
        for execution in instance.execution_set.all():
            if execution.exec_status != Execution.Done:
                execution.exec_status = Execution.Done
                execution.finish_date = instance.actual_finish
                execution.save()
#Change Subtasks status to Done if Task is Done after save Task


class Order(models.Model):
    NotPaid = 'NP'
    AdvancePaid = 'AP'
    PaidUp = 'PU'
    PAYMENT_STATUS_CHOICES = (
        (NotPaid, 'Не оплачений'),
        (AdvancePaid, 'Оплачений аванс'),
        (PaidUp, 'Оплачений')
        )
    contractor = models.ForeignKey(Contractor, verbose_name='Підрядник', on_delete=models.PROTECT)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE)
    order_name = models.CharField('Назва робіт', max_length=30)
    deal_number = models.CharField('Номер договору', max_length=30)
    value = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    advance = models.DecimalField('Аванс, грн.', max_digits=8, decimal_places=2, default=0)
    pay_status = models.CharField('Статус оплати', max_length=2, choices=PAYMENT_STATUS_CHOICES, default=NotPaid)
    pay_date = models.DateField('Дата оплати', blank=True, null=True)

    class Meta:
       unique_together = ('contractor', 'task', 'order_name')
       verbose_name = 'Підрядники'
       verbose_name_plural = 'Підрядник'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.contractor.__str__()

    def save(self, logging=True, *args, **kwargs):
        title = self.task.object_code
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Доданий підрядник по проекту', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлений підрядник по проекту', extra={"title": title})
        super(Order, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = self.task.object_code
        log(user=get_current_user(), action='Видалений підрядник по проекту', extra={"title": title})
        super(Order, self).delete(*args, **kwargs)


class Sending(models.Model):
    receiver = models.ForeignKey(Receiver, verbose_name='Отримувач проекту', on_delete=models.PROTECT)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE)
    receipt_date = models.DateField('Дата відправки')
    copies_count = models.PositiveSmallIntegerField('Кількість примірників', validators=[MaxValueValidator(10)])
    register_num = models.CharField('Реєстр', max_length=30, blank=True)
    comment = models.CharField('Коментар', max_length=100, blank=True)

    class Meta:
        unique_together = ('receiver', 'task', 'receipt_date')
        verbose_name = 'Відправка'
        verbose_name_plural = 'Відправки'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.receiver.__str__()

    def save(self, logging=True, *args, **kwargs):
        title = self.task.object_code
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Додана відправка проекту', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлена відправка проекту', extra={"title": title})
        if self.task.exec_status == Task.Done:
            self.task.exec_status = Task.Sent
            self.task.save()
        super(Sending, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = self.task.object_code
        log(user=get_current_user(), action='Видалена відправка проекту', extra={"title": title})
        super(Sending, self).delete(*args, **kwargs)


class Execution(models.Model):
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано')
    )
    executor = models.ForeignKey(Employee, verbose_name='Виконавець', on_delete=models.PROTECT)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE)
    part_name = models.CharField('Роботи', max_length=100)
    part = models.PositiveSmallIntegerField('Частка', validators=[MaxValueValidator(150)])
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    finish_date = models.DateField('Дата виконання', blank=True, null=True)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('executor', 'task', 'part_name')
        verbose_name = 'Виконавець'
        verbose_name_plural = 'Виконавці'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.executor.__str__()

    def save(self, logging=True, *args, **kwargs):
        title = self.task.object_code + ' ' + self.part_name
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Додана частина проекту', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлена частина проекту', extra={"title": title})
        if self.task.exec_status in [Task.Done, Task.Sent]:
            if self.exec_status != Execution.Done:
                self.exec_status = Execution.Done
                self.finish_date = self.task.actual_finish
        super(Execution, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = self.task.object_code + ' ' + self.part_name
        log(user=get_current_user(), action='Видалена частина проекту', extra={"title": title})
        super(Execution, self).delete(*args, **kwargs)


class IntTask(models.Model):
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В очікуванні'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано')
    )
    task_name = models.CharField('Завдання', max_length=100)
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    executor = models.ForeignKey(Employee, verbose_name='Виконавець', on_delete=models.PROTECT)
    planned_start = models.DateField('Плановий початок робіт', blank=True, null=True)
    planned_finish = models.DateField('Планове закінчення робіт', blank=True, null=True)
    actual_start = models.DateField('Фактичний початок робіт', blank=True, null=True)
    actual_finish = models.DateField('Фактичне закінчення робіт', blank=True, null=True)
    bonus = models.DecimalField('Бонус, грн.', max_digits=8, decimal_places=2, default=0)
    comment = models.TextField('Коментар', blank=True)
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='inttask_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('task_name', 'executor')
        verbose_name = 'Завдання'
        verbose_name_plural = 'Завдання'

    def save(self, logging=True, *args, **kwargs):
        title = self.task_name
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Додане завдання', extra={"title": title})
            else:
                log(user=get_current_user(), action='Оновлене завдання', extra={"title": title})
        super(IntTask, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        log(user=get_current_user(), action='Видалене завдання',
            extra={"title": self.title})
        super(IntTask, self).delete(*args, **kwargs)

    def __str__(self):
        return self.task_name

    def is_editable(self):
        user = get_current_user()
        if user.is_superuser or user == self.creator:
            return True
        else:
            return False

    @staticmethod
    def get_accessable(user):
        return IntTask.objects.all()


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
    creator = models.ForeignKey(User, verbose_name='Створив', on_delete=models.CASCADE)
    created = models.DateField(auto_now_add=True)
    date = models.DateField('Дата')
    next_date = models.DateField('Дата наступної події', blank=True, null=True)
    repeat = models.CharField('Періодичність', max_length=2, choices=REPEAT_CHOICES, default=OneTime)
    title = models.CharField('Назва події', max_length=100)
    description = models.TextField('Опис', blank=True)

    class Meta:
        verbose_name = 'Подія'
        verbose_name_plural = 'Події'

    def save(self, logging=True, *args, **kwargs):
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(), action='Додана подія', extra={"title": self.title})
            else:
                log(user=get_current_user(), action='Оновлена подія', extra={"title": self.title})
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
        return date.today() == self.next_repeat()

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

    def is_editable(self):
        user = get_current_user()
        if user.is_superuser or user == self.creator:
            return True
        else:
            return False
    # try if user has a permitting to edit
