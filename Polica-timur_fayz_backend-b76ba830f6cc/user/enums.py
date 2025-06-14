from django.db import models


class UserType(models.TextChoices):
    ADMIN = "ADMIN", "Администратор"
    MANAGER = "MANAGER", "Менеджер"
    CASHIER = "CASHIER", "Кассир"
    ACCOUNTANT = "ACCOUNTANT", "Бухгалтер"
    TEACHER = "TEACHER", "Учитель"
