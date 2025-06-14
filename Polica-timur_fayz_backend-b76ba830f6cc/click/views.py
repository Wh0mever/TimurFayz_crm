from decimal import Decimal

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView, Response

from payment.services import create_payment
from students.models import Student
from payment.enums import PaymentMethodChoices, PaymentTypeChoices, PaymentModelTypeChoices
from payment.models import Payment
from .click_authorization import click_authorization
from .clickuz import ClickUz
from .models import ClickTransaction
from .serializer import ClickUzSerializer
from .status import *


class ClickUzMerchantAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    VALIDATE_CLASS = None

    def post(self, request):
        serializer = ClickUzSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        METHODS = {
            PREPARE: self.prepare,
            COMPLETE: self.complete
        }

        merchant_trans_id = serializer.validated_data['merchant_trans_id']
        amount = serializer.validated_data['amount']
        action = serializer.validated_data['action']

        if click_authorization(**serializer.validated_data) is False:
            return Response({
                "error": AUTHORIZATION_FAIL_CODE,
                "error_note": AUTHORIZATION_FAIL
            })

        assert self.VALIDATE_CLASS is not None
        check_order = self.VALIDATE_CLASS().check_order(order_id=merchant_trans_id, amount=amount)
        if check_order is True:
            result = METHODS[action](**serializer.validated_data, response_data=serializer.validated_data)
            return Response(result)
        return Response({"error": check_order})

    def prepare(self, click_trans_id: str, merchant_trans_id: str, amount: str, sign_string: str, sign_time: str,
                response_data: dict,
                *args, **kwargs) -> dict:
        """

        :param click_trans_id:
        :param merchant_trans_id:
        :param amount:
        :param sign_string:
        :param response_data:
        :param args:
        :return:
        """
        transaction = ClickTransaction.objects.create(
            click_trans_id=click_trans_id,
            merchant_trans_id=merchant_trans_id,
            amount=amount,
            action=PREPARE,
            sign_string=sign_string,
            sign_datetime=sign_time,
        )
        response_data.update(merchant_prepare_id=transaction.id)
        return response_data

    def complete(self, click_trans_id, amount, error, merchant_prepare_id,
                 response_data, action, *args, **kwargs):
        """

        :param click_trans_id:
        :param merchant_trans_id:
        :param amount:
        :param sign_string:
        :param error:
        :param merchant_prepare_id:
        :param response_data:
        :param action:
        :param args:
        :return:
        """
        try:
            transaction = ClickTransaction.objects.get(pk=merchant_prepare_id)

            if error == A_LACK_OF_MONEY:
                response_data.update(error=A_LACK_OF_MONEY_CODE)
                transaction.action = A_LACK_OF_MONEY
                transaction.status = ClickTransaction.CANCELED
                transaction.save()
                return response_data

            if transaction.action == A_LACK_OF_MONEY:
                response_data.update(error=A_LACK_OF_MONEY_CODE)
                return response_data

            if transaction.amount != amount:
                response_data.update(error=INVALID_AMOUNT)
                return response_data

            if transaction.action == action:
                response_data.update(error=INVALID_ACTION)
                return response_data

            transaction.action = action
            transaction.status = ClickTransaction.FINISHED
            transaction.save()
            response_data.update(merchant_confirm_id=transaction.id)
            self.VALIDATE_CLASS().successfully_payment(transaction.merchant_trans_id, transaction)
            return response_data
        except ClickTransaction.DoesNotExist:
            response_data.update(error=TRANSACTION_NOT_FOUND)
            return response_data


class CheckOrder(ClickUz):
    def check_order(self, order_id: str, amount: str):
        student = Student.objects.filter(account_number=order_id).first()
        if not student:
            return self.ORDER_NOT_FOUND
        # if order.total_cost != Decimal(amount):
        #     return self.INVALID_AMOUNT
        return self.ORDER_FOUND

    def successfully_payment(self, order_id: str, transaction: object):
        student = Student.objects.filter(account_number=order_id).first()
        if not student:
            return self.ORDER_NOT_FOUND
        create_payment(
            payment_type=PaymentTypeChoices.INCOME,
            payment_method=PaymentMethodChoices.CLICK,
            payment_model_type=PaymentModelTypeChoices.STUDENT,
            amount=int(transaction.amount),
            created_user=None,
            payment_date=timezone.now(),
            student=student,
            comment="Пополнение баланса (CLICK)"
        )


class TestView(ClickUzMerchantAPIView):
    VALIDATE_CLASS = CheckOrder
