from django.conf import settings
from django.utils import timezone
from django.db import transaction

from paycomuz import Paycom
from paycomuz.views import MerchantAPIView
from payment.enums import PaymentTypeChoices, PaymentMethodChoices, PaymentModelTypeChoices
from payment.models import Payment
from payment.services import create_payment, process_student_payment_delete
from students.models import Student


class CustomMerchantApiView(MerchantAPIView):

    def order_found(self, validated_data):
        account_number = validated_data['params']['account'][self.KEY]
        student = Student.objects.filter(account_number=account_number).first()
        additional_data = {
            'account_number': student.account_number,
            'account_balance': student.balance,
            'client_name': student.full_name,
            'client_phone': student.phone_number,
        }
        self.reply = dict(result=dict(allow=True, additional=additional_data))


class CheckOrder(Paycom):
    def __init__(self):
        self.ACCOUNT_KEY = settings.PAYCOM_SETTINGS['ACCOUNTS']['KEY']
        super().__init__()

    def check_order(self, amount, account, *args, **kwargs):
        student = Student.objects.filter(account_number=account[self.ACCOUNT_KEY]).first()
        if not student:
            return self.ORDER_NOT_FOND
        if amount > 10000000:
            return self.INVALID_AMOUNT
        return self.ORDER_FOUND

    def successfully_payment(self, data, transaction, *args, **kwargs):
        student = Student.objects.filter(account_number=transaction.order_key).first()
        if not student:
            return self.ORDER_NOT_FOND
        create_payment(
            student=student,
            amount=transaction.amount,
            payment_type=PaymentTypeChoices.INCOME,
            payment_method=PaymentMethodChoices.PAYME,
            payment_model_type=PaymentModelTypeChoices.STUDENT,
            created_user=None,
            comment=f"Пополнение баланса (PAYME): {student.full_name}",
            payme_transaction_id=transaction.id,
        )

    def cancel_payment(self, data, payme_transaction, *args, **kwargs):
        with transaction.atomic():
            payment = Payment.objects.filter(payme_transaction=payme_transaction).first()
            process_student_payment_delete(payment)
            payment.is_deleted = True
            payment.is_active = False
            payment.deleted_at = timezone.now()
            payment.save(update_fields=['is_deleted', 'is_active', 'deleted_at'])


class PaymeCallbackView(CustomMerchantApiView):
    VALIDATE_CLASS = CheckOrder
