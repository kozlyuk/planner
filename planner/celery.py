from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planner.settings')

app = Celery('planner')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'deal_statuses': {
        'task': 'planner.tasks.update_deal_statuses',
        'schedule': crontab(day_of_week="1-5", hour="8-18", minute=0),  # workdays hourly from 8 to 18
    },
    'event_next_date': {
        'task': 'planner.tasks.event_next_date_calculate',
        'schedule': crontab(minute=0, hour=0),                      # at midnight
    },
    'actneed_report': {
        'task': 'planner.tasks.send_actneed_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=0),   # workdays at 8-00
    },
    'debtors_report': {
        'task': 'planner.tasks.send_debtors_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=5),   # workdays at 8-05
    },
    'overdue_deals_report': {
        'task': 'planner.tasks.send_overdue_deals_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=10),  # workdays at 8-10
    },
    'overdue_tasks_report': {
        'task': 'planner.tasks.send_overdue_tasks_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=15),  # workdays at 8-15
    },
    'urgent_tasks_report': {
        'task': 'planner.tasks.send_urgent_tasks_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=20),  # workdays at 8-20
    },
    'unsent_tasks_report': {
        'task': 'planner.tasks.send_unsent_tasks_report',
        'schedule': crontab(day_of_week=1, hour=8, minute=25),    # monday at 8-25
    },
    'monthly_report': {
        'task': 'planner.tasks.send_monthly_report',
        'schedule': crontab(day_of_month=10, hour=17, minute=00),   # on 10th of month at 17-00
    },
}
