from django.conf import settings
from django.db import transaction
from django.db.models import F

from base.sms_service import SMSService
from payment.enums import PaymentTypeChoices, PaymentModelTypeChoices
from payment.exceptions import PaymentSourceNotGiven
from payment.models import Cash, Payment
from students.models import Student
from students.services import increase_student_balance, decrease_student_balance


def increase_cash_amount(cash_id, amount):
    Cash.objects.filter(id=cash_id).update(amount=F('amount') + amount)


def decrease_cash_amount(cash_id, amount):
    Cash.objects.filter(id=cash_id).update(amount=F('amount') - amount)


def add_payment_to_cash(payment: Payment):
    cash_obj, _ = Cash.objects.get_or_create(payment_method=payment.payment_method)
    amount = payment.amount if payment.payment_type == PaymentTypeChoices.INCOME else -payment.amount
    increase_cash_amount(cash_obj.pk, amount)


def delete_payment_from_cash(payment: Payment):
    cash_obj, _ = Cash.objects.get_or_create(payment_method=payment.payment_method)
    amount = payment.amount if payment.payment_type == PaymentTypeChoices.INCOME else -payment.amount
    decrease_cash_amount(cash_obj.pk, amount)


def create_payment(
        payment_type, payment_method, payment_model_type, amount,
        created_user, payment_date, student=None, outlay=None, payme_transaction_id=None, comment=""
):
    with transaction.atomic():
        payment = Payment(
            payment_type=payment_type,
            payment_method=payment_method,
            payment_model_type=payment_model_type,
            amount=amount,
            created_user=created_user,
            payment_date=payment_date,
            comment=comment,
            payme_transaction_id=payme_transaction_id,
        )
        if payment_model_type == PaymentModelTypeChoices.STUDENT:
            if not student:
                raise PaymentSourceNotGiven("Необходимо указать студента")
            payment.student = student
            process_student_payment_create(payment, student)
        elif payment_model_type == PaymentModelTypeChoices.OUTLAY:
            if not outlay:
                raise PaymentSourceNotGiven("Необходимо указать причину расхода")
            payment.outlay = outlay
        payment.save()
        add_payment_to_cash(payment)
    return payment


def process_student_payment_create(payment: Payment, student: Student):
    amount = payment.amount if payment.payment_type == PaymentTypeChoices.INCOME else -payment.amount
    increase_student_balance(student.pk, amount)
    student.refresh_from_db(fields=['balance'])
    payment.student_balance_after = student.balance
    send_sms_to_student(student, settings.STUDENT_PAYMENT_CREATE_SMS_TEMPLATE.format(payment.amount, student.full_name))


def process_payment_delete(payment: Payment):
    if payment.payment_model_type == PaymentModelTypeChoices.STUDENT:
        process_student_payment_delete(payment)
    delete_payment_from_cash(payment)


def process_student_payment_delete(payment: Payment):
    amount = payment.amount if payment.payment_type == PaymentTypeChoices.INCOME else -payment.amount
    decrease_student_balance(payment.student_id, amount)


def send_sms_to_student(student, message):
    phone_numbers = [num for num in [student.phone_number, student.parent_phone_number] if num]
    SMSService().send_mass_sms(phone_numbers, message)
