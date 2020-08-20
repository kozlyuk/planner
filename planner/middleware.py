from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import User
from crum import get_current_user
from messaging.tasks import send_email_list


class ExceptionHandler:
    def __init__(self, get_response):
        self._get_resopnse = get_response

    def __call__(self, request):
        response = self._get_resopnse(request)
        return response

    def process_exception(self, request, exception):
        superuser_email = User.objects.get(username='admin').email
        employee_name = get_current_user().username
        email = EmailMessage(f'Exception happend in {employee_name}',
                             str(exception),
                             settings.DEFAULT_FROM_EMAIL,
                             [superuser_email],
                             )
        send_email_list.delay([email])
