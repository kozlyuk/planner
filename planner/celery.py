from __future__ import absolute_import
import os
import dotenv
from celery import Celery

from dateutil.relativedelta import relativedelta

env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), '.env')
dotenv.read_dotenv(env_file)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planner.settings')

app = Celery('planner', include=['analytics.tasks',
                                 'notice.tasks',
                                 'messaging.tasks',
                                 'html_templates.tasks'
                                 ])

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# this allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'
