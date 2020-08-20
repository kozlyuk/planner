from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab

from datetime import date
from dateutil.relativedelta import relativedelta


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planner.settings')

app = Celery('planner', include=['analytics.tasks',
                                 'notice.tasks',
                                 'messaging.tasks',
                                 ])

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

last_month = date.today() - relativedelta(months=1)

app.conf.beat_schedule = {
    'task_statuses': {
        'task': 'planner.tasks.update_task_statuses',
        # workdays 4 times per hour (8-19)
        'schedule': crontab(day_of_week="1-5", hour="8-19", minute="0,15,30,45"),
    },
    'deal_statuses': {
        'task': 'planner.tasks.update_deal_statuses',
        # workdays hourly from 8 to 18
        'schedule': crontab(day_of_week="1-5", hour="8-18", minute=1),
    },
    'event_next_date': {
        'task': 'notice.tasks.event_next_date_calculate',
        # at midnight
        'schedule': crontab(minute=0, hour=0),
    },
    'actneed_report': {
        'task': 'messaging.tasks.send_actneed_report',
        # workdays at 8-10
        'schedule': crontab(day_of_week="1-5", hour=8, minute=10),
    },
    'debtors_report': {
        'task': 'messaging.tasks.send_debtors_report',
        # workdays at 8-11
        'schedule': crontab(day_of_week="1-5", hour=8, minute=11),
    },
    'overdue_deals_report': {
        'task': 'messaging.tasks.send_overdue_deals_report',
        # workdays at 8-12
        'schedule': crontab(day_of_week="1-5", hour=8, minute=12),
    },
    'overdue_tasks_report': {
        'task': 'messaging.tasks.send_overdue_tasks_report',
        # workdays at 8-20
        'schedule': crontab(day_of_week="1-5", hour=8, minute=20),
    },
    'unsent_tasks_report': {
        'task': 'messaging.tasks.send_unsent_tasks_report',
        # monday at 8-22
        'schedule': crontab(day_of_week=1, hour=8, minute=22),
    },
    'monthly_report': {
        'task': 'messaging.tasks.send_monthly_report',
        # on 10th of month at 17-00
        'schedule': crontab(day_of_month=10, hour=17, minute=00),
    },
    'calc_bonuses': {
        'task': 'analytics.tasks.calc_bonuses',
        # on 10th of month at 07-00
        'schedule': crontab(hour=7, minute=00),
        'args': (last_month.month, last_month.year)
    },
    'calc_bonuses_ed': {
        'task': 'analytics.tasks.calc_bonuses',
        # everyhour
        'schedule': crontab(hour="8-19", minute=5),
        # 'args': (date.today().month, date.today().year)
    },
    'calc_kpi': {
        'task': 'analytics.tasks.calc_kpi',
        # on 10th of month at 07-10
        'schedule': crontab(hour=7, minute=10),
        'args': (last_month.month, last_month.year)
    },
    'calc_kpi_ed': {
        'task': 'analytics.tasks.calc_kpi',
        # everyhour
        'schedule': crontab(hour="8-19", minute=2),
        # 'args': (date.today().month, date.today().year)
    },}
