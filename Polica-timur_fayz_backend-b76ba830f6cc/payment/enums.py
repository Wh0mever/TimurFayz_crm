from django.db.models import TextChoices


class PaymentTypeChoices(TextChoices):
    INCOME = "INCOME", "Приход"
    OUTCOME = "OUTCOME", "Расход"


class PaymentMethodChoices(TextChoices):
    CASH = "CASH", "Наличные"
    CARD = "CARD", "Карта"
    TRANSFER = "TRANSFER", "Перечисление"
    HUMO = "HUMO", "HUMO"
    UZCARD = "UZCARD", "UZCARD"
    CLICK = "CLICK", "CLICK"
    PAYME = "PAYME", "PAYME"
    UZUM = "UZUM", "UZUM"


class PaymentModelTypeChoices(TextChoices):
    STUDENT = "STUDENT", "Студент"
    OUTLAY = "OUTLAY", "Прочие расходы"
