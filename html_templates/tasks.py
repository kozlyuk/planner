""" Tasks for analytics app """
from celery.utils.log import get_task_logger
from weasyprint import HTML, CSS
from django.core.files.uploadedfile import SimpleUploadedFile

from planner.celery import app

LOGGER = get_task_logger(__name__)


@app.task
def generate_pdf(template, context, model, object_pk):
    """ Save monthly bonuses of Employees """

    rendered_html = template.render(context)
    pdf_file = HTML(string=rendered_html).write_pdf()

    try:
        obj = model.objects.get(pk=object_pk)
        obj.pdf_copy = SimpleUploadedFile(obj.number+'.pdf', pdf_file,
                                          content_type='application/pdf')
        obj.save(update_fields=['pdf_copy'], logging=False)

        LOGGER.info("PDF file was created %s", obj.pdf_copy)

    except model.DoesNotExist:
        LOGGER.info("Model object does not exist: %s, %s", model, object_pk)
