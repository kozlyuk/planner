from celery.utils.log import get_task_logger
from planner.celery import app

from .models import Event


logger = get_task_logger(__name__)


@app.task
def event_next_date_calculate():
    """Calculate next_date fields for Events"""
    for event in Event.objects.all():
        event.next_date = event.next_repeat()
        event.save(update_fields=['next_date'], logging=False)
    logger.info("Calculated next_date fields for Events")
