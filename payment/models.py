from django.db import models

from base.models import TimeStampedFlagsModel, FlagsModel
from payment.enums import PaymentTypeChoices, PaymentMethodChoices, PaymentModelTypeChoices
from students.enums import DepartmentChoices


class Payment(TimeStampedFlagsModel):
    payment_type = models.CharField(
        max_length=50,
        choices=PaymentTypeChoices.choices,
        verbose_name="Тип оплаты"
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethodChoices.choices,
        verbose_name="Метод оплаты"
    )
    payment_model_type = models.CharField(
        max_length=50,
        choices=PaymentModelTypeChoices.choices,
        verbose_name="Тип источника оплаты"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name="Студент"
    )
    outlay = models.ForeignKey(
        'payment.OutlayItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name="Прочие расходы"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Сумма"
    )
    student_balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Баланс студента после оплаты"
    )
    payment_date = models.DateTimeField(
        verbose_name="Дата оплаты"
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарий"
    )
    payme_transaction = models.ForeignKey(
        'paycomuz.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name="Payme транзакция"
    )
    marked_for_delete = models.BooleanField(
        default=False,
        verbose_name="Помечен на удаление"
    )

    def __str__(self):
        return f"Платеж #{self.pk}"

    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"

    @property
    def department(self):
        if self.payment_model_type == PaymentModelTypeChoices.STUDENT:
            return self.student.department
        elif self.payment_model_type == PaymentModelTypeChoices:
            return self.outlay.category.department
        return None


class Cash(models.Model):
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethodChoices.choices,
        verbose_name="Метод платежа"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Сумма"
    )

    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.amount}"

    class Meta:
        ordering = ['-id']
        verbose_name = "Касса"
        verbose_name_plural = "Кассы"


class OutlayCategory(FlagsModel):
    title = models.CharField(
        max_length=255,
        verbose_name="Название"
    )
    department = models.CharField(
        max_length=50,
        choices=DepartmentChoices.choices,
        default=DepartmentChoices.SCHOOL,
        verbose_name="Отдел"
    )

    def __str__(self):
        return f"{self.title}"

    class Meta:
        ordering = ['-id']
        verbose_name = "Категория прочих расходов"
        verbose_name_plural = "Категории прочих расходов"


class OutlayItem(FlagsModel):
    category = models.ForeignKey(
        'payment.OutlayCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
        verbose_name="Категория"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Название"
    )

    def __str__(self):
        return f"{self.title}"

    class Meta:
        ordering = ['-id']
        verbose_name = "Прочие расходы"
        verbose_name_plural = "Прочие расходы"
