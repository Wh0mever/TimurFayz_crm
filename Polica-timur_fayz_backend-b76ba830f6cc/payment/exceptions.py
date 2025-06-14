from base.exceptions import BusinessLogicException


class PaymentSourceNotGiven(BusinessLogicException):
    default_detail = "Необходимо указать источник платежа"
    default_code = "payment_source_not_given"
