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
        'schedule': crontab(minute=0, hour=0),  # at midnight
    },
    'actneed_report': {
        'task': 'planner.tasks.send_actneed_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=0),    # workdays at 8-00
    },
    'debtors_report': {
        'task': 'planner.tasks.send_debtors_report',
        'schedule': crontab(day_of_week="1-5", hour=8, minute=5),  # workdays at 8-05
    },
}
