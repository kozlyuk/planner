#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from django.core.validators import MaxValueValidator
from django.db.models import Sum
from django.conf.locale.uk import formats as uk_formats


date_format = uk_formats.DATE_INPUT_FORMATS[0]


class Employee(models.Model):
    user = models.OneToOneField(User)
    name = models.CharField('ПІБ', max_length=50, unique=True)
    position = models.CharField('Посада', max_length=50)
    head = models.ForeignKey('self', verbose_name='Кервіник', on_delete=models.SET_NULL, blank=True, null=True)
    phone = models.CharField('Телефон', max_length=13, blank=True)
    mobile_phone = models.CharField('Мобільний телефон', max_length=13, blank=True)
    birthday = models.DateField('День народження', blank=True, null=True)
    salary = models.DecimalField('Заробітна плата, грн.', max_digits=8, decimal_places=2, default=0)
    vacation_count = models.PositiveSmallIntegerField('Кількість днів відпустки', blank=True, null=True,
                                                      validators=[MaxValueValidator(100)])
    vacation_date = models.DateField('Дата нарахування відпустки', blank=True, null=True)

    class Meta:
        verbose_name = 'Працівник'
        verbose_name_plural = 'Працівники'

    def __str__(self):
        return self.name

    def owner_count(self):
        active = 0
        overdue = 0
        for task in self.task_set.exclude(exec_status=Task.Done):
            active += 1
            if task.overdue_status().startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    owner_count.short_description = 'Керівник проектів'

    def task_count(self):
        active = 0
        overdue = 0
        for task in self.tasks.exclude(exec_status=Task.Done):
            active += 1
            if task.overdue_status().startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    task_count.short_description = 'Виконавець в проектах'

    def inttask_count(self):
        active = self.inttask_set.exclude(exec_status=IntTask.Done).count()
        overdue = self.inttask_set.exclude(exec_status=IntTask.Done).exclude(planned_finish__gte=date.today()).count()
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    inttask_count.short_description = 'Завдання'

    def bonuses_calc_new(self, delta):
        bonuses = 0
        month = datetime.now().month + delta
        year = datetime.now().year
        if month < 1:
            month += 12
            year += -1

        executions = self.execution_set.filter(part__gt=0, task__exec_status=Task.Done,
                                               task__actual_finish__month=month,
                                               task__actual_finish__year=year)
        for query in executions:
            bonuses += query.task.exec_bonus(query.part)
        # executor bonus

        tasks = self.task_set.filter(exec_status=Task.Done,
                                     actual_finish__month=month,
                                     actual_finish__year=year)
        for query in tasks:
            bonuses += query.owner_bonus()
        # owner bonus

        inttasks = self.inttask_set.filter(exec_status=IntTask.Done,
                                           actual_finish__month=month,
                                           actual_finish__year=year)
        for query in inttasks:
            bonuses += query.bonus
        # inttask bonus

        return round(bonuses, 2)

    def bonuses_cm(self):
        return self.bonuses_calc_new(0)
    bonuses_cm.short_description = 'Бонуси {}.{}'.format(datetime.now().month, datetime.now().year)

    def bonuses_pm(self):
        return self.bonuses_calc_new(-1)
    bonuses_pm.short_description = 'Бонуси {}.{}'\
        .format(datetime.now().month -1 if datetime.now().month >1 else datetime.now().month + 11,
                datetime.now().year if datetime.now().month >1 else datetime.now().year - 1)

    def bonuses_ppm(self):
        return self.bonuses_calc_new(-2)
    bonuses_ppm.short_description = 'Бонуси {}.{}'\
        .format(datetime.now().month -2 if datetime.now().month >2 else datetime.now().month + 10,
                datetime.now().year if datetime.now().month >2 else datetime.now().year - 1)


class Customer(models.Model):
    name = models.CharField('Назва', max_length=100, unique=True)
    contact_person = models.CharField('Контактна особа', max_length=50)
    phone = models.CharField('Телефон', max_length=13)
    email = models.EmailField('Email')
    requisites = models.TextField('Реквізити', blank=True)

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
    customer = models.ForeignKey(Customer, verbose_name='Замовник')
    price_code = models.CharField('Пункт кошторису', max_length=8)
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
        unique_together = ('project_type', 'price_code')
        verbose_name = 'Вид робіт'
        verbose_name_plural = 'Види робіт'
        ordering = ['price_code']

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
    name = models.CharField('Назва', max_length=100, unique=True)
    chief = models.ForeignKey(Employee, verbose_name='Керівник')
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
    name = models.CharField('Назва', max_length=100, unique=True)
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
    customer = models.ForeignKey(Customer, verbose_name='Замовник')
    company = models.ForeignKey(Company, verbose_name='Компанія')
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
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('number', 'customer')
        verbose_name = 'Договір'
        verbose_name_plural = 'Договори'

    def __str__(self):
        return self.number + ' ' + self.customer.name

    def __init__(self, *args, **kwargs):
        super(Deal, self).__init__(*args, **kwargs)
        self.__customer__= None

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
        return 'Відсутні проекти'
    exec_status.short_description = 'Статус виконання'

    def overdue_status(self):
        if 'загальний' in self.number:
            return ''
        if self.exec_status() == 'Виконано':
            value_calc = self.value_calc() + self.value_correction
            if self.value > 0 and self.value != value_calc:
                return 'Вартість по роботам %s' % value_calc
            if self.act_status == self.NotIssued:
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
            total += task.project_type.price
        return round(total, 2)
    value_calc.short_description = 'Вартість договору по роботам, грн.'

    def costs_calc(self):                                            # total deal's costs
        total = 0
        for task in self.task_set.all():
            total += task.costs_total()
        return round(total, 2)
    costs_calc.short_description = 'Витрати по договору, грн.'


class Receiver(models.Model):
    customer = models.ForeignKey(Customer, verbose_name='Замовник')
    name = models.CharField('Отримувач', max_length=100, unique=True)
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
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано')
    )
    object_code = models.CharField('Шифр об’єкту', max_length=30)
    object_address = models.CharField('Адреса об’єкту', max_length=255)
    project_type = models.ForeignKey(Project, verbose_name='Тип проекту')
    ts_date = models.DateField('Дата отримання ТЗ', blank=True, null=True)
    project_code = models.CharField('Шифр проекту', max_length=30, blank=True)
    deal = models.ForeignKey(Deal, verbose_name='Договір')
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    owner = models.ForeignKey(Employee, verbose_name='Керівник проекту')
    executors = models.ManyToManyField(Employee, through='Execution', related_name='tasks',
                                       verbose_name='Виконавці', blank=True)
    costs =  models.ManyToManyField(Contractor, through='Order', related_name='tasks',
                                    verbose_name='Підрядники', blank=True)
    planned_start = models.DateField('Плановий початок робіт', blank=True, null=True)
    planned_finish = models.DateField('Планове закінчення робіт', blank=True, null=True)
    actual_start = models.DateField('Фактичний початок робіт', blank=True, null=True)
    actual_finish = models.DateField('Фактичне закінчення робіт', blank=True, null=True)
    letter_send = models.DateField('Відправлено лист-запит', blank=True, null=True)
    receivers = models.ManyToManyField(Receiver, through='Sending', verbose_name='Отримувачі проекту')
    comment = models.TextField('Коментар', blank=True)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('object_code', 'project_type', 'deal')
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекти'

    def __str__(self):
        return self.object_code + ' ' + self.project_type.__str__()

    def overdue_status(self):
        if self.exec_status == self.Done:
            if self.receivers.all():
                if self.receivers.all().aggregate(Sum('sending__copies_count')).get('sending__copies_count__sum') \
                        < self.project_type.copies_count:
                    return 'Не всі відправки'
            elif self.project_type.copies_count > 0:
                return 'Не відправлено'
            return 'Виконано %s' % self.actual_finish.strftime(date_format)
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
    # displays task overdue warnings

    def is_active(self):
        if not self.actual_finish:
            return True
        if self.actual_finish.month >= (datetime.now().month + 12*(datetime.now().year-self.actual_finish.year)-1):
            if self.actual_finish.month == datetime.now().month:
                return True
            if datetime.now().day < 6:
                return True
        return False
    # try if task edit period is not expired

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

    def total_bonus(self):
        return self.exec_bonus(self.exec_part() - self.outsourcing_part()) + self.owner_bonus()
    # total bonus


class Order(models.Model):
    NotPaid = 'NP'
    AdvancePaid = 'AP'
    PaidUp = 'PU'
    PAYMENT_STATUS_CHOICES = (
        (NotPaid, 'Не оплачений'),
        (AdvancePaid, 'Оплачений аванс'),
        (PaidUp, 'Оплачений')
        )
    contractor = models.ForeignKey(Contractor, verbose_name='Підрядник')
    task = models.ForeignKey(Task, verbose_name='Проект')
    order_name = models.CharField('Назва робіт', max_length=30)
    deal_number = models.CharField('Номер договору', max_length=30)
    value = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    advance = models.DecimalField('Аванс, грн.', max_digits=8, decimal_places=2, default=0)
    pay_status = models.CharField('Статус оплати', max_length=2, choices=PAYMENT_STATUS_CHOICES, default=NotPaid)
    pay_date = models.DateField('Дата оплати', blank=True, null=True)

    class Meta:
       unique_together = ('contractor', 'task', 'order_name')
       verbose_name = 'Витрати'
       verbose_name_plural = 'Витрати'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.contractor.__str__()


class Sending(models.Model):
    receiver = models.ForeignKey(Receiver, verbose_name='Отримувач проекту')
    task = models.ForeignKey(Task, verbose_name='Проект')
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


class Execution(models.Model):
    executor = models.ForeignKey(Employee, verbose_name='Виконавець')
    task = models.ForeignKey(Task, verbose_name='Проект')
    part_name = models.CharField('Назва робіт', max_length=100)
    part = models.PositiveSmallIntegerField('Частка робіт', validators=[MaxValueValidator(150)])

    class Meta:
        unique_together = ('executor', 'task', 'part_name')
        verbose_name = 'Виконавець'
        verbose_name_plural = 'Виконавці'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.executor.__str__()


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
    executor = models.ForeignKey(Employee, verbose_name='Виконавець')
    planned_start = models.DateField('Плановий початок робіт', blank=True, null=True)
    planned_finish = models.DateField('Планове закінчення робіт', blank=True, null=True)
    actual_start = models.DateField('Фактичний початок робіт', blank=True, null=True)
    actual_finish = models.DateField('Фактичне закінчення робіт', blank=True, null=True)
    bonus = models.DecimalField('Бонус, грн.', max_digits=8, decimal_places=2, default=0)
    comment = models.TextField('Коментар', blank=True)

    class Meta:
        unique_together = ('task_name', 'executor')
        verbose_name = 'Завдання'
        verbose_name_plural = 'Завдання'

    def __str__(self):
        return self.task_name


class Calendar(models.Model):
    OneTime = 'OT'
    RepeatWeekly = 'RW'
    RepeatMonthly = 'RM'
    RepeatQuaterly = 'RQ'
    RepeatYearly = 'RY'
    EXEC_STATUS_CHOICES = (
        (OneTime, 'Одноразова подія'),
        (RepeatWeekly, 'Щотижнева подія'),
        (RepeatMonthly, 'Щомісячна подія'),
        (RepeatQuaterly, 'Щоквартальна подія'),
        (RepeatYearly, 'Щорічна подія')
    )
    creator = models.ForeignKey(Employee, verbose_name='Створив')
    created = models.DateField(auto_now_add=True)
    repeat = models.CharField('Періодичність', max_length=2, choices=EXEC_STATUS_CHOICES, default=OneTime)
    title = models.CharField('Назва події', max_length=100)
    description =  models.TextField('Опис', blank=True)

    class Meta:
        verbose_name = 'Подія'
        verbose_name_plural = 'Події'

    def __str__(self):
        return self.title


class News(models.Model):
    creator = models.ForeignKey(Employee, verbose_name='Створив')
    created = models.DateField(auto_now_add=True)
    title = models.CharField('Назва новини', max_length=100)
    text =  models.TextField('Новина')

    class Meta:
        verbose_name = 'Новина'
        verbose_name_plural = 'Новини'

    def __str__(self):
        return self.title
