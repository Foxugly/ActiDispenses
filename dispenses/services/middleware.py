import logging

from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from dispenses.services.oracle import OracleServiceError

logger = logging.getLogger(__name__)


class OracleUnavailableMiddleware(MiddlewareMixin):
    @staticmethod
    def process_exception(request, exception):
        if not isinstance(exception, OracleServiceError):
            return None

        logger.exception("Oracle service error - %s returned", exception.status_code)
        return render(
            request,
            "errors/503_db.html",
            {
                "status_code": exception.status_code,
                "title": exception.title,
                "message": exception.user_message,
            },
            status=exception.status_code,
        )
