# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from django.db import models
from django.db.models import Sum, Max
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.urls import reverse
from django.core.validators import MaxValueValidator
from django.conf.locale.uk import formats as uk_formats
from django.dispatch import receiver
from django.apps import apps
from crum import get_current_user
from decimal import Decimal, ROUND_HALF_UP

from stdimage.models import StdImageField
from eventlog.models import log
from html_templates.models import HTMLTemplate

from .mixins import ModelDiffMixin
from .formatChecker import ContentTypeRestrictedFileField
from .managers import DealQuerySet, ActQuerySet, PaymentQuerySet
from .timeplanning import TimePlanner


date_format = uk_formats.DATE_INPUT_FORMATS[0]


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/projects/user_<id>/Year/Month/<filename>
    return 'projects/user_{0}/{1}/{2}/{3}'\
        .format(get_current_user().id, date.today().year, date.today().month, filename)


def avatar_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/avatar/user_<id>/<filename>
    return 'avatars/user_{0}/{1}'\
        .format(get_current_user().id, filename)


class Construction(models.Model):

    name = models.CharField('Тип конструкції', max_length=100, unique=True)
    description = models.CharField('Опис', max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'Тип конструкції'
        verbose_name_plural = 'Типи конструкцій'
        ordering = ['name']

    def __str__(self):
        return self.name


class WorkType(models.Model):

    name = models.CharField('Вид будівництва', max_length=100, unique=True)
    description = models.CharField('Опис', max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'Вид будівництва'
        verbose_name_plural = 'Види будівництва'
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    name = models.CharField('ПІБ', max_length=30, unique=True)
    position = models.CharField('Посада', max_length=50)
    head = models.ManyToManyField('self', verbose_name='Керівники', symmetrical=False, blank=True)
    phone = models.CharField('Телефон', max_length=13, blank=True)
    mobile_phone = models.CharField('Мобільний телефон', max_length=13, blank=True)
    avatar = StdImageField('Фото', upload_to=avatar_directory_path, default='avatars/no_image.jpg',
                           variations={'large': (400, 400, True), 'thumbnail': (100, 100, True), })
    birthday = models.DateField('День народження', blank=True, null=True)
    salary = models.DecimalField('Заробітна плата, грн.', max_digits=8, decimal_places=2, default=0)
    coefficient = models.PositiveSmallIntegerField('Коєфіцієнт плану', default=50,
                                                   validators=[MaxValueValidator(200)])
    vacation_count = models.PositiveSmallIntegerField('Кількість днів відпустки', blank=True, null=True,
                                                      validators=[MaxValueValidator(100)])
    vacation_date = models.DateField('Дата нарахування відпустки', blank=True, null=True)
    card_number = models.CharField('Номер карти', max_length=19, blank=True)
    comment = models.TextField('Коментар', blank=True)

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
            if task.warning.startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    owner_count.short_description = 'Керівник проектів'

    def task_count(self):
        active = 0
        overdue = 0
        for task in self.tasks.exclude(exec_status=Task.Sent):
            active += 1
            if task.warning.startswith('Протерміновано'):
                overdue += 1
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    task_count.short_description = 'Виконавець в проектах'

    def inttask_count(self):
        active = self.inttask_set.exclude(exec_status=IntTask.Done).count()
        overdue = self.inttask_set.exclude(exec_status=IntTask.Done)\
                                  .exclude(planned_finish__gte=date.today()).count()
        return 'Активні-' + str(active) + '/Протерміновані-' + str(overdue)
    inttask_count.short_description = 'Завдання'

    def tasks_for_period(self, period):
        """ return queryset with tasks for given month """
        return self.task_set.filter(sending_date__month=period.month,
                                    sending_date__year=period.year)

    def executions_for_period(self, period):
        """ return queryset with executions for given month """
        return self.execution_set.filter(exec_status=Execution.Done,
                                         actual_finish__month=period.month,
                                         actual_finish__year=period.year)

    def inttasks_for_period(self, period):
        """ return queryset with inttasks for given month """
        return self.inttask_set.filter(actual_finish__month=period.month,
                                       actual_finish__year=period.year)

    def overdue_tasks(self):
        """ return queryset with overdue tasks of task owner """
        return self.task_set.exclude(exec_status__in=[Task.Done, Task.Sent,
                                                      Task.OnHold, Task.Canceled]) \
                            .exclude(deal__expire_date__gte=date.today(),
                                     planned_finish__isnull=True) \
                            .exclude(deal__expire_date__gte=date.today(),
                                     planned_finish__gte=date.today())

    def overdue_executions(self):
        """ return queryset with overdue executions of employee """
        return self.execution_set.exclude(exec_status__in=[Execution.Done, Execution.OnChecking]) \
                                 .exclude(planned_finish__gte=date.today())

    def overdue_inttasks(self):
        """ return queryset with overdues inttasks of employee """
        return self.inttask_set.exclude(exec_status=IntTask.Done) \
                               .exclude(planned_finish__gte=date.today())

    def unsent_tasks(self):
        """ return queryset with tasks tasks of task owner """
        return self.task_set.filter(exec_status=Task.Done)

    def is_subordinate(self):
        # try if user has a permitting to edit the task
        user = get_current_user()
        if user.is_superuser or \
            user.groups.filter(name='Бухгалтери').exists() or \
            user.employee == self or \
            user.employee in self.head.all():
            return True


class Requisites(models.Model):
    name = models.CharField('Назва', max_length=50, unique=True)
    full_name = models.CharField('Повна назва', max_length=100, blank=True)
    edrpou = models.CharField('ЄДРПОУ', max_length=10, blank=True)
    city = models.CharField('Місто', max_length=30, blank=True)
    legal = models.CharField('Опис контрагента', max_length=255, blank=True)
    legal_description = models.CharField('Організаційно-правова форма', max_length=255, blank=True)
    regulations = models.CharField('Діє на підставі', max_length=100, blank=True)
    signatory_person = models.CharField('Підписант', max_length=50, blank=True)
    signatory_position = models.CharField('Посада підписанта', max_length=255, blank=True)
    requisites = models.TextField('Реквізити', blank=True)

    class Meta:
        abstract = True


class Customer(Requisites):
    contact_person = models.CharField('Контактна особа', max_length=50)
    phone = models.CharField('Телефон', max_length=13)
    email = models.EmailField('Email')
    debtor_term = models.PositiveSmallIntegerField('Термін післяоплати', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, blank=True, null=True)
    plan_reserve = models.DurationField('Запас плану', default=timedelta(hours=8))
    deal_template = models.ForeignKey(HTMLTemplate, verbose_name='Шаблон договору', blank=True, null=True, on_delete=models.CASCADE, related_name='customers_deals')
    act_template = models.ForeignKey(HTMLTemplate, verbose_name='Шаблон акту', blank=True, null=True, on_delete=models.CASCADE, related_name='customers_acts')
    invoice_template = models.ForeignKey(HTMLTemplate, verbose_name='Шаблон рахунку', blank=True, null=True, on_delete=models.CASCADE, related_name='customers_invoices')
    report_template = models.ForeignKey(HTMLTemplate, verbose_name='Шаблон звіту', blank=True, null=True, on_delete=models.CASCADE, related_name='customers_reports')
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Замовник'
        verbose_name_plural = 'Замовники'

    def __str__(self):
        return self.name

    def debit_calc(self):
        total = 0
        for deal in self.deal_set.exclude(exec_status=Deal.Canceled):
            if deal.pay_status != Deal.PaidUp:
                acts_total = deal.acts_total()
                paid_total = deal.paid_total()
                if acts_total > paid_total:
                    total += acts_total - paid_total
        return u'{0:,}'.format(total).replace(u',', u' ')
    debit_calc.short_description = 'Дебіторська заборгованість {}'.format(
        date.today().year)

    def credit_calc(self):
        total = 0
        for deal in self.deal_set.exclude(exec_status=Deal.Canceled):
            if deal.pay_status != Deal.NotPaid:
                acts_total = deal.acts_total()
                paid_total = deal.paid_total()
                if acts_total < paid_total:
                    total += paid_total - acts_total
        return u'{0:,}'.format(total).replace(u',', u' ')
    credit_calc.short_description = 'Авансові платежі'

    def completed_calc(self):
        total = 0
        for deal in self.deal_set.exclude(exec_status=Deal.Canceled).filter(expire_date__year=date.today().year):
            if deal.pay_status != Deal.NotPaid or deal.act_status != Deal.NotIssued:
                total += min(deal.acts_total(), deal.paid_total())
        return u'{0:,}'.format(total).replace(u',', u' ')
    completed_calc.short_description = 'Виконано та оплачено {}'.format(
        date.today().year)

    def expect_calc(self):
        total = 0
        for deal in self.deal_set.exclude(exec_status=Deal.Canceled):
            if deal.pay_status == Deal.NotPaid and deal.act_status == Deal.NotIssued:
                total += deal.value - deal.paid_total()
        return u'{0:,}'.format(total).replace(u',', u' ')
    expect_calc.short_description = 'В роботі'


class Project(models.Model):
    project_type = models.CharField('Вид робіт', max_length=100)
    customer = models.ForeignKey(Customer, verbose_name='Замовник', on_delete=models.PROTECT)
    price_code = models.CharField('Пункт кошторису', max_length=15, unique=True)
    price = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    net_price_rate = models.PositiveSmallIntegerField('Вартість після вхідних витрат, %',
                                                      validators=[MaxValueValidator(100)], default=75)
    owner_bonus = models.PositiveSmallIntegerField('Бонус керівника проекту, %',
                                                   validators=[MaxValueValidator(100)], default=6)
    executors_bonus = models.PositiveSmallIntegerField('Бонус виконавців, %',
                                                       validators=[MaxValueValidator(100)], default=12)
    copies_count = models.PositiveSmallIntegerField('Кількість примірників', default=0,
                                                    validators=[MaxValueValidator(10)])
    need_project_code = models.BooleanField('Потрібен шифр проекту', default=True)
    description = models.TextField('Опис', blank=True)
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Вид робіт'
        verbose_name_plural = 'Види робіт'
        ordering = ['-price_code']

    def __str__(self):
        return f"{self.price_code} {self.project_type}"

    def net_price(self):
        net_price = self.price * self.net_price_rate / 100
        return round(net_price, 2)
    net_price.short_description = 'Вартість після вхідних витрат'

    def turnover_calc(self):
        total = 0
        for task in self.task_set.filter(actual_finish__year=date.today().year):
            total += task.project_type.price
        return u'{0:,}'.format(total).replace(u',', u' ')
    turnover_calc.short_description = 'Оборот по пункту'


class Company(Requisites):
    TAXATION_CHOICES = (
        ('wvat', 'З ПДВ'),
        ('wovat', 'Без ПДВ'),
    )
    chief = models.ForeignKey(Employee, verbose_name='Керівник', related_name='company_chiefs', on_delete=models.PROTECT)
    accountant = models.ForeignKey(Employee, verbose_name='Бухгалтер', related_name='company_accountant', on_delete=models.PROTECT)
    taxation = models.CharField('Система оподаткування', max_length=5, choices=TAXATION_CHOICES, default='wvat')
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Компанія'
        verbose_name_plural = 'Компанії'

    def __str__(self):
        return self.name

    def turnover_calc(self):
        total = 0
        for deal in self.deal_set.filter(date__year=date.today().year):
            acts_total = deal.acts_total()
            total += acts_total
        return u'{0:,}'.format(total).replace(u',', u' ')
    turnover_calc.short_description = 'Оборот {}'.format(date.today().year)

    def costs_calc(self):
        total = 0
        for deal in self.deal_set.filter(date__year=date.today().year):
            total += deal.costs_calc()
        return u'{0:,}'.format(total).replace(u',', u' ')
    costs_calc.short_description = 'Витрати {}'.format(date.today().year)

    def bonuses_calc(self):
        total = 0
        for deal in self.deal_set.filter(date__year=date.today().year):
            total += deal.bonuses_calc()
        return u'{0:,}'.format(total).replace(u',', u' ')
    bonuses_calc.short_description = 'Бонуси {}'.format(date.today().year)


class Contractor(models.Model):
    name = models.CharField('Назва', max_length=50, unique=True)
    edrpou = models.CharField('ЄДРПОУ', max_length=10, blank=True)
    contact_person = models.CharField('Контактна особа', max_length=50, blank=True)
    phone = models.CharField('Телефон', max_length=13, blank=True)
    email = models.EmailField('Email', blank=True)
    requisites = models.TextField('Реквізити', blank=True)
    active = models.BooleanField('Активний', default=True)

    class Meta:
        verbose_name = 'Контрагент'
        verbose_name_plural = 'Контрагенти'

    def __str__(self):
        return self.name

    def advance_calc(self):
        total = 0
        for order in self.order_set.exclude(task__exec_status__in=[Task.Done, Task.Sent, Task.Canceled]):
            if order.pay_status == Order.AdvancePaid:
                total += order.advance
            if order.pay_status == Order.PaidUp:
                total += order.value
        return u'{0:,}'.format(total).replace(u',', u' ')
    advance_calc.short_description = 'Авансові платежі'

    def credit_calc(self):
        total = 0
        for order in self.order_set.filter(task__exec_status__in=[Task.Done, Task.Sent]):
            if order.pay_status == Order.NotPaid:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.value - order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    credit_calc.short_description = 'Кредиторська заборгованість'

    def expect_calc(self):
        total = 0
        for order in self.order_set.exclude(task__exec_status__in=[Task.Done, Task.Sent]):
            if order.pay_status == Order.NotPaid:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.value - order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    expect_calc.short_description = 'Не виконано та не оплачено'

    def completed_calc(self):
        total = 0
        for order in self.order_set.filter(task__exec_status__in=[Task.Done, Task.Sent],
                                           pay_date__year=date.today().year):
            if order.pay_status == Order.PaidUp:
                total += order.value
            if order.pay_status == Order.AdvancePaid:
                total += order.advance
        return u'{0:,}'.format(total).replace(u',', u' ')
    completed_calc.short_description = 'Виконано та оплачено'


class Deal(ModelDiffMixin, models.Model):
    NotPaid = 'NP'
    AdvancePaid = 'AP'
    PartlyPaid = 'PP'
    PaidUp = 'PU'
    PAYMENT_STATUS_CHOICES = (
        (NotPaid, 'Не оплачений'),
        (AdvancePaid, 'Оплачений аванс'),
        (PartlyPaid, 'Оплачений частково'),
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
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    Sent = 'ST'
    Canceled = 'CL'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано'),
        (Sent, 'Надіслано'),
        (Canceled, 'Відмінено')
    )
    SPECIFIC_STATUS_CHOICES = (
        ('WF', 'Всі договори'),
        ('WA', 'Чекають закриття актів'),
        ('PQ', 'Черга оплат'),
        ('OP', 'Протермінована опата'),
        ('RE', 'Дебіторська заборгованість'),
        ('OE', 'Протеріноване виконання'),
    )

    number = models.CharField('Номер договору', max_length=30)
    date = models.DateField('Дата договору', default=now)
    parent_deal_number = models.CharField('Номер генерального договору', max_length=30, blank=True, null=True)
    parent_deal_date = models.DateField('Дата генерального договору', blank=True, null=True)
    customer = models.ForeignKey(Customer, verbose_name='Замовник', on_delete=models.PROTECT)
    company = models.ForeignKey(Company, verbose_name='Компанія', on_delete=models.PROTECT)
    value = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    advance = models.DecimalField('Аванс, грн.', max_digits=8, decimal_places=2, default=0)
    value_correction = models.DecimalField('Коригування вартості робіт, грн.',
                                           max_digits=8, decimal_places=2, default=0)
    pay_status = models.CharField('Статус оплати', max_length=2, choices=PAYMENT_STATUS_CHOICES, default=NotPaid)
    expire_date = models.DateField('Дата закінчення договору')
    act_status = models.CharField('Акт виконаних робіт', max_length=2, choices=ACT_STATUS_CHOICES, default=NotIssued)
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    warning = models.CharField('Попередження', max_length=30, blank=True)
    manual_warning = models.CharField('Попередження', max_length=30, blank=True)
    pdf_copy = ContentTypeRestrictedFileField('Електронний примірник', upload_to=user_directory_path,
                                              content_types=['application/pdf',
                                                             'application/vnd.openxmlformats-officedocument.'
                                                             'spreadsheetml.sheet',
                                                             'application/vnd.openxmlformats-officedocument.'
                                                             'wordprocessingml.document'],
                                              max_upload_size=26214400,
                                              blank=True, null=True)
    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='deal_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    # defining custom manager
    objects = DealQuerySet.as_manager()

    class Meta:
        unique_together = ('number', 'customer')
        verbose_name = 'Договір'
        verbose_name_plural = 'Договори'
        ordering = ['-creation_date', 'customer', '-number']

    def __str__(self):
        return self.number + ' ' + self.customer.name

    def get_absolute_url(self):
        return reverse('deal_update', args=[self.pk])

    def save(self, *args, logging=True, **kwargs):

        # Automatic changing of deal statuses
        self.act_status = self.get_act_status()
        self.pay_status = self.get_pay_status()

        # Update deal value
        if self.act_status != Deal.Issued:
            self.value = self.value_calc()

        # Logging
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(),
                    action='Доданий договір',
                    extra={'title': self.number},
                    obj=self,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлений договір',
                    extra={'title': self.number, 'diff': self.diff_str},
                    obj=self,
                    )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        log(user=get_current_user(),
            action='Видалений договір',
            extra={'title': self.number},
            obj=self,
            )
        super().delete(*args, **kwargs)

    def get_act_status(self):
        # Get actual act_status
        if self.actofacceptance_set.count() > 0:
            value_sum = self.actofacceptance_set.aggregate(Sum('value'))['value__sum'] or 0
            if value_sum >= self.value + self.value_correction:
                return self.Issued
            elif value_sum > 0:
                return self.PartlyIssued
        return self.NotIssued

    def get_pay_status(self):
        # Get actual pay_status
        if self.payment_set.exists():
            act_sum = self.actofacceptance_set.aggregate(Sum('value'))['value__sum'] or 0
            payment_sum = self.payment_set.aggregate(Sum('value'))['value__sum'] or 0
            if payment_sum > act_sum:
                return self.AdvancePaid
            elif payment_sum > 0 and act_sum > payment_sum:
                return self.PartlyPaid
            elif act_sum == payment_sum == self.value + self.value_correction:
                return self.PaidUp
        return self.NotPaid

    def svalue(self):
        return u'{0:,}'.format(self.value).replace(u',', u' ')
    svalue.short_description = 'Вартість робіт, грн.'

    def bonuses_calc(self):
        """ total deal's bonuses """
        total = 0
        for task in self.task_set.all():
            total += task.total_bonus()
        return round(total, 2)
    bonuses_calc.short_description = 'Бонуси по договору, грн.'

    def value_calc(self):
        """ Total deal's price """
        total = 0
        for task in self.task_set.all():
            price = task.project_type.price
            if self.company.taxation == 'wovat':
                price = price / 6 * 5
            total += price
        return round(total, 2)
    value_calc.short_description = 'Вартість договору по роботам, грн.'

    def costs_calc(self):
        """ total deal's costs """
        total = 0
        for task in self.task_set.all():
            total += task.costs_total()
        return round(total, 2)
    costs_calc.short_description = 'Витрати по договору, грн.'

    def pay_date_calc(self):
        """ total deal's costs """
        if self.customer.debtor_term:
            last_act = self.actofacceptance_set.order_by('date').last()
            if last_act:
                return last_act.date + timedelta(days=self.customer.debtor_term)
    pay_date_calc.short_description = 'Дата оплати'

    def acts_total(self):
        """ total act's value """
        return self.actofacceptance_set.aggregate(total=Sum('value')).get('total') or 0

    def paid_total(self):
        """ total paid value """
        return self.payment_set.aggregate(total=Sum('value')).get('total') or 0


@receiver(post_save, sender=Deal, dispatch_uid="update_deal_status")
def update_deal(sender, instance, **kwargs):
    """ Update Deals status after save Deal """
    from planner.tasks import update_deal_statuses
    update_deal_statuses(instance.pk)


class ActOfAcceptance(ModelDiffMixin, models.Model):

    deal = models.ForeignKey(Deal, verbose_name='Договір', on_delete=models.PROTECT)
    number = models.CharField('Номер акту виконаних робіт', max_length=30)
    date = models.DateField('Дата акту виконаних робіт')
    value = models.DecimalField('Сума акту виконаних робіт, грн.', max_digits=8, decimal_places=2, default=0)
    pdf_copy = ContentTypeRestrictedFileField('Електронний примірник', upload_to=user_directory_path,
                                              content_types=['application/pdf',
                                                             'application/vnd.openxmlformats-officedocument.'
                                                             'spreadsheetml.sheet',
                                                             'application/vnd.openxmlformats-officedocument.'
                                                             'wordprocessingml.document'],
                                              max_upload_size=26214400,
                                              blank=True, null=True)
    comment = models.CharField('Коментар', blank=True, max_length=255)
    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='act_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    # defining custom manager
    objects = ActQuerySet.as_manager()

    class Meta:
        unique_together = ('number', 'deal')
        verbose_name = 'Акт виконаних робіт'
        verbose_name_plural = 'Акти виконаних робіт'
        ordering = ['-creation_date', '-number']

    def __str__(self):
        return f'{self.number} від {self.date}'

    def save(self, *args, logging=True, **kwargs):

        # tasks actofacceptance autofill
        if self.deal.get_act_status() == Deal.Issued:
            if self.deal.actofacceptance_set.count() == 1:
                self.deal.task_set.update(act_of_acceptance=self)

        # Logging
        if logging:
            title = f'{self.number} - {self.date}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Доданий акт',
                    extra={'title': title},
                    obj=self.deal,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлений акт',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self.deal,
                    )

        if not self.pk:
            # Set creator
            self.creator = get_current_user()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # update tasks with this act
        self.task_set.update(act_of_acceptance = None)
        # logging
        title = f'{self.number} - {self.date}'
        log(user=get_current_user(),
            action='Видалений акт',
            extra={'title': title},
            obj=self.deal,
            )
        super().delete(*args, **kwargs)


class PaymentBase(ModelDiffMixin, models.Model):
    date = models.DateField('Дата оплати')
    value = models.DecimalField('Сума, грн.', max_digits=8, decimal_places=2, default=0)
    purpose = models.CharField('Призначення платежу', max_length=255, blank=True)
    doc_number = models.CharField('Документ', max_length=10, blank=True)
    comment = models.CharField('Коментар', blank=True, max_length=255)
    # Creating information
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        abstract = True


class Payment(PaymentBase):
    deal = models.ForeignKey(Deal, verbose_name='Договір', on_delete=models.PROTECT)
    act_of_acceptance = models.ForeignKey(ActOfAcceptance, verbose_name='Акт виконаних робіт',
                                          blank=True, null=True, on_delete=models.SET_NULL)
    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='peyment_creators', on_delete=models.PROTECT)

    # defining custom manager
    objects = PaymentQuerySet.as_manager()

    class Meta:
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплати'
        ordering = ['-creation_date', 'deal']

    def __str__(self):
        return f'{self.deal} - {self.date}'

    def save(self, *args, logging=True, **kwargs):

        # Logging
        if logging:
            title = f'{self.date} - {self.value}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Додана оплата',
                    extra={'title': title},
                    obj=self.deal,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлена оплата',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self.deal,
                    )

        if not self.pk:
            # Set creator
            self.creator = get_current_user()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = f'{self.date} - {self.value}'
        log(user=get_current_user(),
            action='Видалена оплата',
            extra={'title': title},
            obj=self.deal,
            )
        super().delete(*args, **kwargs)


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


class Task(ModelDiffMixin, models.Model):
    ToDo = 'IW'
    InProgress = 'IP'
    Done = 'HD'
    Sent = 'ST'
    OnHold = 'OH'
    Canceled = 'CL'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (Done, 'Виконано'),
        (Sent, 'Надіслано'),
        (OnHold, 'Призупинено'),
        (Canceled, 'Відмінено')
    )
    object_code = models.CharField('Шифр об’єкту', max_length=30)
    object_address = models.CharField('Адреса об’єкту', max_length=255)
    project_type = models.ForeignKey(Project, verbose_name='Тип проекту', on_delete=models.PROTECT)
    project_code = models.IntegerField('Шифр проекту', blank=True, null=True)
    deal = models.ForeignKey(Deal, verbose_name='Договір', on_delete=models.PROTECT)
    construction = models.ForeignKey(Construction, verbose_name='Тип конструкції', on_delete=models.PROTECT, blank=True, null=True)
    work_type = models.ForeignKey(WorkType, verbose_name='Вид будівництва', on_delete=models.PROTECT, blank=True, null=True)
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    warning = models.CharField('Попередження', max_length=30, blank=True)
    manual_warning = models.CharField('Примітка', max_length=30, blank=True)
    owner = models.ForeignKey(Employee, verbose_name='Керівник проекту', on_delete=models.PROTECT)
    executors = models.ManyToManyField(Employee, through='Execution', related_name='tasks',
                                       verbose_name='Виконавці', blank=True)
    costs = models.ManyToManyField(Contractor, through='Order', related_name='tasks',
                                   verbose_name='Підрядники', blank=True)
    planned_start = models.DateField('Плановий початок', blank=True, null=True)
    planned_finish = models.DateField('Планове закінчення', blank=True, null=True)
    actual_start = models.DateField('Фактичний початок', blank=True, null=True)
    actual_finish = models.DateField('Фактичне закінчення', blank=True, null=True)
    sending_date = models.DateField('Дата відправки', blank=True, null=True)
    period = models.DateField('Період проектування', blank=True, null=True)
    tc_received = models.DateField('Отримано ТЗ', blank=True, null=True)
    tc_upload = ContentTypeRestrictedFileField('Технічне завдання', upload_to=user_directory_path,
        content_types=['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                       max_upload_size=26214400, blank=True, null=True)
    receivers = models.ManyToManyField(Receiver, through='Sending', verbose_name='Отримувачі проекту')
    pdf_copy = ContentTypeRestrictedFileField('Електронний примірник', upload_to=user_directory_path,
        content_types=['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                       max_upload_size=26214400, blank=True, null=True)
    difficulty_owner = models.DecimalField('Коефіцієнт ведення', max_digits=3, decimal_places=2, default=1)
    difficulty_executor = models.DecimalField('Коефіцієнт виконання', max_digits=3, decimal_places=2, default=1)
    act_of_acceptance = models.ForeignKey(ActOfAcceptance, verbose_name='Акт виконаних робіт',
                                          blank=True, null=True, on_delete=models.SET_NULL)
    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='task_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)
    project_share = models.CharField('Папка проекту', max_length=255, blank=True, null=True)
    photo_share = models.CharField('Папка фото', max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('object_code', 'project_type', 'deal')
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекти'
        ordering = ['-creation_date', '-deal', 'object_code']

    def __str__(self):
        return f"{self.object_code} {self.project_type}"

    def get_absolute_url(self):
        return reverse('task_detail', args=[self.pk])

    def get_last_comment(self):
        Comment =apps.get_model('notice.Comment')
        last_comment = Comment.objects.filter(content_type__model='Task',
                                      object_id=self.pk)
        return last_comment.latest('timestamp').text[:50] if last_comment else None

    def save(self, *args, logging=True, **kwargs):

        # Logging
        if logging:
            title = f'{self.object_code} {self.project_type.price_code}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Доданий проект',
                    extra={'title': title},
                    obj=self,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлений проект',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self,
                    )

        is_new_object = False
        if not self.pk:
            is_new_object = True
            # Set creator
            self.creator = get_current_user()
            # Automatic set project_code
            if self.project_type.need_project_code:
                self.project_code = Task.objects.aggregate(Max('project_code'))['project_code__max'] + 1

        # Automatic change Task.exec_status when Execution has changed
        if self.execution_set.filter(exec_status__in=[Execution.InProgress, Execution.OnChecking, Execution.Done]).exists() \
                and self.exec_status == self.ToDo:
            self.exec_status = self.InProgress

         # Automatic set actual_finish when Task has done
        if self.exec_status in [self.Done, self.Sent] and self.actual_finish is None:
            self.actual_finish = date.today()
        elif self.exec_status not in [self.Done, self.Sent] and self.actual_finish is not None:
            self.actual_finish = None

        # Automatic changing of Task.exec_status when all sendings was sent
        if self.exec_status in [self.Done, self.Sent]:
            sendings = self.sending_set.aggregate(Sum('copies_count'))['copies_count__sum'] or 0
            if not self.sending_date and sendings > 0:
                self.exec_status = self.Sent
                self.sending_date = self.sending_set.filter(copies_count__gt=0).first().receipt_date

        super().save(*args, **kwargs)

        # Automatic change Executions.exec_status when Task status changed
        for execution in self.execution_set.all():
            if self.exec_status in [self.Done, self.Sent] \
                and execution.exec_status != Execution.Done:
                execution.exec_status = Execution.Done
                execution.save()
            elif self.exec_status in [self.OnHold, self.Canceled] \
                and execution.exec_status not in [Execution.OnHold, Execution.Done]:
                execution.exec_status = Execution.OnHold
                execution.save()

        # Automatic create basic subtasks
        if is_new_object:
            for subtask in self.project_type.subtask_set.filter(base=True):
                Execution.objects.create(task=self,
                                         subtask=subtask,
                                         part = subtask.part,
                                         )

    def delete(self, *args, **kwargs):
        title = f'{self.object_code} {self.project_type.price_code}'
        log(user=get_current_user(),
            action='Видалений проект',
            extra={'title': title},
            obj=self,
            )
        super(Task, self).delete(*args, **kwargs)

    def execution_status(self):
        """Show task status by subtasks"""
        queryset = self.execution_set.values_list('exec_status', flat=True)
        if Execution.ToDo in queryset:
            return 'В черзі'
        if Execution.InProgress in queryset:
            return 'Виконується'
        if Execution.Done in queryset:
            return 'Виконано'
        return 'Відсутні виконавці'
    execution_status.short_description = 'Статус виконання частин проекту'

    def sending_status(self):
        try:
            if self.receivers.all().aggregate(Sum('sending__copies_count')).get('sending__copies_count__sum') \
                    < self.project_type.copies_count:
                return 'Не всі відправки'
        except TypeError:
            if self.project_type.copies_count > 0:
                return 'Не надіслано'
        return 'Надіслано'
    sending_status.short_description = 'Статус відправки'

    def is_active(self):
        # check if task edit period is not expired
        if not self.actual_finish:
            return True
        if self.actual_finish.month == date.today().month and self.actual_finish.year == date.today().year:
            return True
        if (date.today() - self.actual_finish).days < 7:
            return True
        return False

    def is_viewable(self):
        # check if user has a permitting to view the task
        user = get_current_user()
        if user.is_superuser:
            return True
        elif user == self.owner.user or self.executors.filter(user=user).exists() \
                or self.executors.filter(head__user=user).exists():
            return True
        elif user.groups.filter(name='Бухгалтери').exists():
            return True
        elif user.groups.filter(name='Секретарі').exists():
            return True
        elif user.groups.filter(name='Замовники').exists():
            return True
        else:
            return False

    def is_editable(self):
        # check if user has a permitting to edit the task
        user = get_current_user()
        if user.is_superuser:
            return True
        elif self.is_active() and user == self.owner.user:
            return True
        elif user.groups.filter(name__in=['Бухгалтери', 'Секретарі']).exists():
            return True
        else:
            return False

    def costs_total(self):
        costs = self.costs.all().aggregate(Sum('order__value')).get('order__value__sum')
        return costs if costs is not None else 0
    # total task's costs

    def exec_part(self):
        part = self.executors.all().aggregate(
            Sum('execution__part')).get('execution__part__sum')
        return part if part is not None else 0
    # executors part

    def outsourcing_part(self):
        part = self.executors.filter(user__username__startswith='outsourcing').aggregate(Sum('execution__part'))\
            .get('execution__part__sum')
        return part if part is not None else 0
    # outsourcing part

    def owner_part(self):
        if self.project_type.owner_bonus > 0:
            if self.exec_part() > 100:
                return int(100 + (100 - self.exec_part()) *
                       self.project_type.executors_bonus / self.project_type.owner_bonus)
            return 100
        return 0
    owner_part.short_description = "Частка"
    # owner part

    def owner_bonus(self):
        bonus = (self.project_type.net_price() - self.costs_total()) * self.owner_part()\
            * self.project_type.owner_bonus / 10000 * self.difficulty_owner
        return bonus.quantize(Decimal("1.00"), ROUND_HALF_UP) if bonus > 0 else Decimal(0)
    owner_bonus.short_description = "Бонус"
    # owner's bonus

    def exec_bonus(self, part):
        bonus = self.project_type.net_price() * part * self.project_type.executors_bonus / 10000  * self.difficulty_executor
        return bonus.quantize(Decimal("1.00"), ROUND_HALF_UP)
    exec_bonus.short_description = "Бонус"
    # executor's bonus

    def executors_bonus(self):
        return self.exec_bonus(self.exec_part())
    # executors bonuses

    def total_bonus(self):
        return self.exec_bonus(self.exec_part() - self.outsourcing_part()) + self.owner_bonus()
    # total bonus

    # list of executions for task_list
    def executions(self):
        line = ""
        execitions = self.execution_set.filter(subtask__show_to_customer=True)
        for execution in execitions:
            line += f'\n{execution.subtask.name} - {execution.get_exec_status_display()}'
            if execution.exec_status == Execution.Done and execution.actual_finish:
                line += f" - {execution.actual_finish.strftime(date_format)}"
            elif execution.planned_finish:
                line += f" - {execution.planned_finish.strftime(date_format)}"
        return line[1:]

    def money_earned(self, part):
        return self.project_type.net_price() * part / 100


@receiver(post_save, sender=Task, dispatch_uid="update_task_status")
def update_task(sender, instance, **kwargs):
    """ Update Tasks status after save Task"""
    from planner.tasks import update_task_statuses
    update_task_statuses(instance.pk)


class SubTask(models.Model):

    project_type = models.ForeignKey(Project, verbose_name='Тип проекту', on_delete=models.PROTECT)
    name = models.CharField('Назва робіт', max_length=100)
    part = models.PositiveSmallIntegerField('Частка від проекту', default=0, validators=[MaxValueValidator(100)])
    duration = models.DurationField('Тривалість виконання', default=timedelta(hours=8))
    base = models.BooleanField('Базова', default=False)
    add_to_schedule = models.BooleanField('Додавати в календар', default=True)
    simultaneous_execution = models.BooleanField('Одночасне виконання', default=False)
    check_required = models.BooleanField('Потрібна перевірка', default=True)
    show_to_customer = models.BooleanField('Показувати замовнику', default=False)

    class Meta:
        unique_together = ('project_type', 'name')
        verbose_name = 'Підзадача'
        verbose_name_plural = 'Підзадачі'
        ordering = ['project_type', '-base']

    def __str__(self):
        return self.name


class Order(ModelDiffMixin, models.Model):
    NotPaid = 'NP'
    Approved = 'AR'
    AdvancePaid = 'AP'
    AdvanceApproved = 'AA'
    PaidUp = 'PU'
    PAYMENT_STATUS_CHOICES = (
        (NotPaid, 'Нове замовлення'),
        (Approved, 'Погоджена оплата'),
        (AdvanceApproved, 'Погоджений аванс'),
        (AdvancePaid, 'Оплачений аванс'),
        (PaidUp, 'Оплачене')
    )
    BankPaymentVAT = 'BV'
    BankPayment = 'BP'
    CashPayment = 'CP'
    PAYMENT_TYPE_CHOICES = (
        (BankPaymentVAT, 'Платіж з ПДВ'),
        (BankPayment, 'Платіж без ПДВ'),
        (CashPayment, 'Готівка')
    )
    ProjectCost = 'PC'
    TripCost = 'TC'
    OfficeCost = 'OC'
    СlericalCost = 'CC'
    FixedAssets = 'FA'
    UtilityPayments = 'UP'
    LaborCosts = 'LC'
    Taxes = 'TA'
    COST_TYPE_CHOICES = (
        (ProjectCost, 'Проектні витрати'),
        (TripCost, 'Відрядні витрати'),
        (OfficeCost, 'Офісні витрати'),
        (СlericalCost, 'Канцелярські витрати'),
        (FixedAssets, 'Основні засоби'),
        (UtilityPayments, 'Комунальні платежі'),
        (LaborCosts, 'Оплата праці'),
        (Taxes, 'Податки'),
    )
    contractor = models.ForeignKey(Contractor, verbose_name='Підрядник', on_delete=models.PROTECT)
    company = models.ForeignKey(Company, verbose_name='Компанія', on_delete=models.PROTECT)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE, blank=True, null=True)
    subtask = models.ForeignKey(SubTask, verbose_name='Підзадача', blank=True, null=True, on_delete=models.SET_NULL)
    purpose = models.CharField('Призначення', max_length=50, blank=True)
    cost_type = models.CharField('Стаття затрат', max_length=2, choices=COST_TYPE_CHOICES, default=ProjectCost)
    deal_number = models.CharField('Договір/замовлення', max_length=50, blank=True)
    value = models.DecimalField('Вартість робіт, грн.', max_digits=8, decimal_places=2, default=0)
    advance = models.DecimalField('Аванс, грн.', max_digits=8, decimal_places=2, default=0)
    pay_type = models.CharField('Форма оплати', max_length=2, choices=PAYMENT_TYPE_CHOICES, default=BankPaymentVAT)
    pay_status = models.CharField('Статус оплати', max_length=2, choices=PAYMENT_STATUS_CHOICES, default=NotPaid)
    pay_date = models.DateField('Планова дата оплати', blank=True, null=True)
    approved_date = models.DateField('Дата погодження', blank=True, null=True)
    approved_by = models.ForeignKey(User, verbose_name='Погоджено', related_name='order_peyment_approvers',
                                    blank=True, null=True, on_delete=models.PROTECT)
    warning = models.CharField('Попередження', max_length=30, blank=True)
    deal = ContentTypeRestrictedFileField('Договір', upload_to=user_directory_path,
                                          content_types=['application/pdf',
                                                         'application/vnd.openxmlformats-officedocument.'
                                                         'spreadsheetml.sheet',
                                                         'application/vnd.openxmlformats-officedocument.'
                                                         'wordprocessingml.document'
                                                         ],
                                          max_upload_size=26214400,
                                          blank=True, null=True
                                          )
    invoice = ContentTypeRestrictedFileField('Рахунок', upload_to=user_directory_path,
                                             content_types=['application/pdf',
                                                            'application/vnd.openxmlformats-officedocument.'
                                                            'spreadsheetml.sheet',
                                                            'application/vnd.openxmlformats-officedocument.'
                                                            'wordprocessingml.document'
                                                            ],
                                             max_upload_size=26214400,
                                             blank=True, null=True
                                             )

    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив', related_name='order_creators',
                                on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Замовлення'
        verbose_name_plural = 'Замовлення'
        ordering = ['-creation_date']

    def __str__(self):
        if self.subtask:
            return f'{self.contractor} - {self.subtask}'
        elif self.purpose:
            return f'{self.contractor} - {self.purpose}'
        else:
            return str(self.contractor)

    def get_absolute_url(self):
        return reverse('order_update', args=[self.pk])

    def save(self, *args, logging=True, **kwargs):

        # Set creator
        if not self.pk:
            self.creator = get_current_user()

        # Automatic set Company
        if not self.pk and self.task:
            self.company = self.task.deal.company

        # Automatic changing of pay status
        self.pay_status = self.get_pay_status()

        # logging
        title = str(self)
        if logging:
            if not self.pk:
                log(user=get_current_user(),
                    action='Додане замовлення',
                    extra={'title': title},
                    obj=self,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлене замовлення',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self,
                    )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = str(self)
        log(user=get_current_user(),
            action='Видалений підрядник по проекту',
            extra={'title': title},
            obj=self,
            )
        super().delete(*args, **kwargs)

    def get_exec_status(self):
        return self.task.get_exec_status_display() if self.task else ''
    get_exec_status.short_description = 'Статус виконання'

    def get_actual_finish(self):
        if self.task:
            return self.task.actual_finish
    get_actual_finish.short_description = 'Дата виконання'

    def get_pay_status(self):
        # Get actual pay_status
        payment_sum = self.orderpayment_set.aggregate(Sum('value'))['value__sum'] or 0
        if payment_sum == self.value:
            return self.PaidUp
        if self.advance:
            if self.approved_date and payment_sum < self.advance:
                return self.AdvanceApproved
            if self.approved_date and payment_sum >= self.advance:
                return self.Approved
            if payment_sum >= self.advance:
                return self.AdvancePaid
        else:
            if self.approved_date:
                return self.Approved
            if payment_sum > 0:
                return self.AdvancePaid
        return self.NotPaid

    def can_approve(self):
        if get_current_user().is_superuser and self.pay_status in [self.NotPaid, self.AdvancePaid] and self.pay_date:
            return True

    def can_cancell_approve(self):
        if get_current_user().is_superuser and self.pay_status in [self.AdvanceApproved, self.Approved]:
            return True

    def approve(self):
        # Approve order
        user = get_current_user()
        if self.can_approve():
            self.approved_by = user
            self.approved_date = date.today()
            self.save(logging=False)
            # logging
            title = str(self)
            log(user=user,
                action='Погоджене замовлення',
                extra={'title': title},
                obj=self,
                )
            # send email for accountant
            if self.pay_date == date.today() and self.pay_type != self.CashPayment:
                from messaging.tasks import send_payment_notification
                send_payment_notification.delay(self.pk)

    def cancel_approval(self):
        # Cancel approval of order
        if self.can_cancell_approve():
            self.approved_by = None
            self.approved_date = None
            self.save(logging=False)
            # logging
            title = str(self)
            log(user=get_current_user(),
                action='Відміна погодження замовлення',
                extra={'title': title},
                obj=self,
                )


class OrderPayment(PaymentBase):
    order = models.ForeignKey(Order, verbose_name='Замовлення', on_delete=models.CASCADE)
    # Creating information
    creator = models.ForeignKey(User, verbose_name='Створив',
                                related_name='order_peyment_creators',
                                on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Оплата замовлення'
        verbose_name_plural = 'Оплати замовлень'
        ordering = ['-creation_date', 'order']

    def __str__(self):
        return f'{self.date} - {self.value}'

    def save(self, *args, logging=True, **kwargs):

        # Logging
        if logging:
            title = f'{self.date} - {self.value}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Додана оплата замовлення',
                    extra={'title': title},
                    obj=self.order,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлена оплата замовлення',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self.order,
                    )

        if not self.pk:
            # Set creator
            self.creator = get_current_user()
            # reset approving when advance paid
            if self.order.pay_status == Order.AdvanceApproved and self.order.advance <= self.value < self.order.value:
                self.order.approved_date = None
                self.order.approved_by = None
                self.order.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        title = f'{self.date} - {self.value}'
        log(user=get_current_user(),
            action='Видалена оплата замовлення',
            extra={'title': title},
            obj=self.order,
            )
        super().delete(*args, **kwargs)


class Sending(ModelDiffMixin, models.Model):
    receiver = models.ForeignKey(Receiver, verbose_name='Отримувач проекту', on_delete=models.CASCADE)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE)
    receipt_date = models.DateField('Дата відправки')
    copies_count = models.PositiveSmallIntegerField('Кількість примірників', validators=[MaxValueValidator(10)])
    register_num = models.CharField('Реєстр', max_length=30, blank=True)
    comment = models.CharField('Коментар', max_length=255, blank=True)

    class Meta:
        unique_together = ('receiver', 'task', 'receipt_date')
        verbose_name = 'Відправка'
        verbose_name_plural = 'Відправки'

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.receiver.__str__()

    def save(self, *args, logging=True, **kwargs):

        # Logging
        if logging:
            title = f'{self.task.object_code} {self.task.project_type.price_code}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Додана відправка проекту',
                    extra={'title': title},
                    obj=self.task,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлена відправка проекту',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self.task,
                    )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        # Automatic changing of Task.exec_status when sendings was deleted
        sendings = self.task.sending_set.aggregate(Sum('copies_count'))['copies_count__sum'] or 0
        sendings -= self.copies_count
        if self.task.exec_status == Task.Sent and sendings < self.task.project_type.copies_count:
            self.task.exec_status = Task.Done
            self.task.sending_date = None
            self.task.save(logging=False)

        # Logging
        title = f'{self.task.object_code} {self.task.project_type.price_code}'
        log(user=get_current_user(),
            action='Видалена відправка проекту',
            extra={'title': title},
            obj=self.task,
            )
        super().delete(*args, **kwargs)


class Execution(ModelDiffMixin, models.Model):
    ToDo = 'IW'
    InProgress = 'IP'
    OnHold = 'OH'
    OnChecking = 'OC'
    Done = 'HD'
    EXEC_STATUS_CHOICES = (
        (ToDo, 'В черзі'),
        (InProgress, 'Виконується'),
        (OnHold, 'Призупинено'),
        (OnChecking, 'На перевірці'),
        (Done, 'Виконано')
    )
    executor = models.ForeignKey(Employee, verbose_name='Виконавець', blank=True, null=True, on_delete=models.PROTECT)
    task = models.ForeignKey(Task, verbose_name='Проект', on_delete=models.CASCADE)
    subtask = models.ForeignKey(SubTask, verbose_name='Підзадача', on_delete=models.PROTECT)
    part = models.PositiveSmallIntegerField('Частка', default=0, validators=[MaxValueValidator(150)])
    exec_status = models.CharField('Статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, default=ToDo)
    prev_exec_status = models.CharField('Попередный статус виконання', max_length=2, choices=EXEC_STATUS_CHOICES, blank=True, null=True)
    planned_start = models.DateTimeField('Плановий початок', blank=True, null=True)
    planned_finish = models.DateTimeField('Планове закінчення', blank=True, null=True)
    actual_start = models.DateTimeField('Початок виконання', blank=True, null=True)
    actual_finish = models.DateTimeField('Кінець виконання', blank=True, null=True)
    work_started = models.DateTimeField('Початок роботи', blank=True, null=True)
    fixed_date = models.BooleanField('Зафіксувати дату', default=False)
    interruption = models.DurationField('Тривалість переривання', default=timedelta(0))
    actual_duration = models.DurationField('Тривалість виконання', default=timedelta(0))
    warning = models.CharField('Попередження', max_length=30, blank=True)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Виконавець'
        verbose_name_plural = 'Виконавці'
        ordering = ['creation_date']

    def __str__(self):
        return self.task.__str__() + ' --> ' + self.executor.__str__()

    @property
    def planned_duration(self):
        if self.planned_start and self.planned_finish:
            timeplanner = TimePlanner(self.executor)
            return timeplanner.calc_businesshrsdiff(self.planned_start, self.planned_finish)

    @property
    def planned_finish_with_interruption(self):
            timeplanner = TimePlanner(self.executor)
            return timeplanner.planned_finish_with_interruption(self)

    def save(self, *args, logging=True, **kwargs):

        # Remove planned_start planned_finish when executor field empty
        if self.executor is None:
            self.planned_start = None
            self.planned_finish = None
            self.prev_exec_status = self.ToDo
            self.exec_status = self.ToDo
        else:
            # Automatic add execution first to employee queue with duration 1 hour
            timeplanner = TimePlanner(self.executor)
            if self.exec_status == self.ToDo and self.prev_exec_status in [self.OnChecking, self.Done] \
                    and self.planned_start and self.warning != "На коригуванні":
                self.warning = "На коригуванні"
                self.planned_finish = timeplanner.calc_businesstimedelta(self.planned_start, timedelta(hours=1))
            if self.exec_status == self.OnChecking and self.warning == "На коригуванні":
                self.warning = ""

            # Automatic set actual_start and work_started when exec_status has changed
            if self.exec_status == self.InProgress and not self.actual_start:
                self.actual_start = datetime.now()
            if self.exec_status == self.InProgress and not self.work_started:
                self.work_started = datetime.now()

            # Automatic set actual_duration when exec_status has changed
            if self.exec_status in [self.OnHold, self.OnChecking, self.Done] and self.work_started:
                self.actual_duration += timeplanner.calc_businesshrsdiff(self.work_started, datetime.now())
                self.work_started = None

            # Automatic set actual_finish when Execution has done
            if self.exec_status == self.Done and not self.actual_finish:
                self.actual_finish = datetime.now()
            elif self.exec_status != self.Done and self.actual_finish:
                self.actual_finish = None

            # Automatic set planned_finish when execution was not planned and has done
            if self.exec_status == self.Done and not self.planned_finish:
                self.planned_finish = datetime.now()

        # Logging
        if logging:
            title = f'{self.task.object_code} {self.task.project_type.price_code} {self.subtask.name}'
            if not self.pk:
                log(user=get_current_user(),
                    action='Додана задача',
                    extra={'title': title},
                    obj=self.task,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлена задача',
                    extra={'title': title, 'diff': self.diff_str},
                    obj=self.task,
                    )
        super().save(*args, **kwargs)

        # Recal employee execution queue
        if self.executor:
            timeplanner.recalc_queue()

    def delete(self, *args, **kwargs):
        title = f'{self.task.object_code} {self.task.project_type.price_code} {self.subtask.name}'
        log(user=get_current_user(),
            action='Видалена задача',
            extra={'title': title},
            obj=self.task,
            )
        super().delete(*args, **kwargs)

    def warning_select(self):
        """Show subtask warning if it exist. Else show task warning"""
        if self.warning:
            return self.warning
        if self.planned_finish and self.exec_status != self.Done:
            if self.planned_finish.date() < date.today():
                return 'Протерміновано %s' % self.planned_finish.strftime(date_format)
            return 'Завершити до %s' % self.planned_finish.strftime(date_format)
        return self.task.warning
    warning_select.short_description = 'Попередження'

    def is_active(self):
        """ Show if subtask edit period is not expired
            Return False if subtask Done more than 20 days ago
        """
        # if execution is not Done return True
        if self.exec_status != Execution.Done:
            return True
        # if execution doesn't have date return True
        if not self.actual_finish:
            return True
        # if date in current month return True
        if self.actual_finish.month == date.today().month and self.actual_finish.year == date.today().year:
            return True
        # if date less than 10 days from today return True
        date_delta = datetime.now() - self.actual_finish
        if date_delta.days < 20:
            return True
        return False


class IntTask(ModelDiffMixin, models.Model):
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
    creator = models.ForeignKey(User, verbose_name='Створив',
                                related_name='inttask_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('task_name', 'executor')
        verbose_name = 'Завдання'
        verbose_name_plural = 'Завдання'
        ordering = ['-exec_status', '-actual_finish']

    def save(self, *args, logging=True, **kwargs):

        # Automatic set actual_finish when IntTask has done
        if self.exec_status == Task.Done and self.actual_finish is None:
            self.actual_finish = date.today()
        elif self.exec_status != Execution.Done and self.actual_finish is not None:
            self.actual_finish = None

        # Logging
        if not self.pk:
            self.creator = get_current_user()
        if logging:
            if not self.pk:
                log(user=get_current_user(),
                    action='Додане завдання',
                    extra={'title': self.task_name},
                    obj=self,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлене завдання',
                    extra={'title': self.task_name, 'diff': self.diff_str},
                    obj=self,
                    )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        log(user=get_current_user(),
            action='Видалене завдання',
            extra={'title': self.task_name},
            obj=self,
            )
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.task_name

    def get_absolute_url(self):
        return reverse('inttask_detail', args=[self.pk])

    def is_editable(self):
        user = get_current_user()
        return user.is_superuser or user == self.creator


class Vacation(ModelDiffMixin, models.Model):

    employee = models.ForeignKey(Employee, verbose_name='Працівник', on_delete=models.CASCADE)
    start_date = models.DateField('Початок відпустки')
    end_date = models.DateField('Кінець відпустки')
    creator = models.ForeignKey(User, verbose_name='Створив',
                                related_name='vacation_creators', on_delete=models.PROTECT)
    creation_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'start_date')
        verbose_name = 'Відпустка'
        verbose_name_plural = 'Відпустки'
        ordering = ['-creation_date']

    def __str__(self):
        return f'{self.employee} {self.start_date}-{self.end_date}'

    def save(self, *args, logging=True, **kwargs):
        # Automatic set creator
        if not self.pk:
            self.creator = get_current_user()

        # Logging
        if logging:
            if not self.pk:
                log(user=get_current_user(),
                    action='Додана відпустка',
                    extra={'title': self.employee.name},
                    obj=self,
                    )
            elif self.diff_str:
                log(user=get_current_user(),
                    action='Оновлена відпустка',
                    extra={'title': self.employee.name, 'diff': self.diff_str},
                    obj=self,
                    )
        super().save(*args, **kwargs)

        timeplanner = TimePlanner(self.employee)
        timeplanner.recalc_queue()


# class Plan(models.Model):

#     name = models.CharField('Назва плану', max_length=100)
#     executors = models.ManyToManyField(Employee, through='Execution', related_name='tasks',
#                                        verbose_name='Виконавці', blank=True)
#     part = models.PositiveSmallIntegerField('Відсоток виконання', default=0, validators=[MaxValueValidator(100)])
#     planned_start = models.DateField('Плановий початок робіт', blank=True, null=True)
#     planned_finish = models.DateField('Планове закінчення робіт', blank=True, null=True)
#     bonus = models.DecimalField('Бонус, грн.', max_digits=8, decimal_places=2, default=0)
#     comment = models.TextField('Коментар', blank=True)
#     creator = models.ForeignKey(User, verbose_name='Створив',
#                                 related_name='inttask_creators', on_delete=models.PROTECT)
#     creation_date = models.DateField(auto_now_add=True)

#     class Meta:
#         unique_together = ('task_name', 'executor')
#         verbose_name = 'Завдання'
#         verbose_name_plural = 'Завдання'
#         ordering = ['-exec_status', '-actual_finish']
