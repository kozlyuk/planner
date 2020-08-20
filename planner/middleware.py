import logging
from crum import get_current_user


logger = logging.getLogger(__name__)


class ExceptionHandler:
    def __init__(self, get_response):
        self._get_resopnse = get_response

    def __call__(self, request):
        response = self._get_resopnse(request)
        return response

    def process_exception(self, request, exception):
        employee_name = get_current_user().username
        logger.exception("Fatal exception happend in %s", employee_name)
