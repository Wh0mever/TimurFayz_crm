from django.db.models import IntegerChoices, TextChoices


class DaysOfWeek(IntegerChoices):
    MONDAY = 1, "Понедельник"
    TUESDAY = 2, "Вторник"
    WEDNESDAY = 3, "Среда"
    THURSDAY = 4, "Четверг"
    FRIDAY = 5, "Пятница"
    SATURDAY = 6, "Суббота"
    SUNDAY = 7, "Воскресенье"


class Gender(TextChoices):
    MALE = "MALE", "Мужчина"
    FEMALE = "FEMALE", "Женщина"


class DepartmentChoices(TextChoices):
    SCHOOL = "SCHOOL", "Школа"
    KINDERGARTEN = "KINDERGARTEN", "Детский сад"
    CAMP = "CAMP", "Лагерь"
