from rest_framework.views import exception_handler
from rest_framework.response import Response
from .exceptions import BusinessLogicException

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, BusinessLogicException):
        return Response(
            data={'detail': exc.detail, 'code': exc.code},
            status=exc.status_code
        )

    return response