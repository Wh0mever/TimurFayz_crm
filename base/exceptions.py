class BusinessLogicException(Exception):
    status_code = 400
    default_detail = 'A business logic error occurred.'
    default_code = 'business_logic_error'

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail

        if code is not None:
            self.code = code
        else:
            self.code = self.default_code


class SMSSendRequestFailed(BusinessLogicException):
    default_detail = 'SMS sending failed'
    default_code = 'sms_send_failed'
