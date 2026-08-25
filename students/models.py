from functools import cached_property

from django.db import models
from django.utils import timezone

from base.models import TimeStampedFlagsModel, FlagsModel, TimeStampedModel
from students.enums import DaysOfWeek, Gender, DepartmentChoices
from students.managers import StudentQuerySet, StudentGroupQuerySet


class StudyGroup(TimeStampedFlagsModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Название"
    )
    start_date = models.DateField(
        verbose_name="Дата начала"
    )
    end_date = models.DateField(
        verbose_name="Дата конца"
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Цена"
    )
    teacher = models.ForeignKey(
        'user.Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='groups',
        verbose_name="Преподаватель"
    )
    department = models.CharField(
        max_length=50,
        choices=DepartmentChoices.choices,
        default=DepartmentChoices.KINDERGARTEN,
        verbose_name="Отдел"
    )
    marked_for_delete = models.BooleanField(
        default=False,
        verbose_name="Помечен на удаление"
    )

    objects = StudentGroupQuerySet.as_manager()

    # days_of_week = ArrayField(
    #     models.IntegerField(choices=DaysOfWeek.choices),
    #     verbose_name="Дни недели занятий",
    #     default=[]
    # )

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ['-id']
        verbose_name = "Учебная группа"
        verbose_name_plural = "Учебные группы"


class StudyGroupDay(models.Model):
    group = models.ForeignKey(
        'students.StudyGroup',
        on_delete=models.CASCADE,
        related_name='study_days',
        verbose_name="Группа"
    )
    day_of_week = models.IntegerField(
        choices=DaysOfWeek.choices,
        verbose_name="День недели"
    )
    start_time = models.TimeField(
        verbose_name="Время начала занятия"
    )

    def __str__(self):
        return f"{self.group} | {self.get_day_of_week_display()}"

    class Meta:
        ordering = ['day_of_week']
        verbose_name = "День занятий"
        verbose_name_plural = "Дни занятий"
        unique_together = [['group', 'day_of_week']]


class StudyLesson(models.Model):
    group = models.ForeignKey(
        'students.StudyGroup',
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Группа"
    )
    date = models.DateTimeField(
        verbose_name="Дата занятия"
    )

    def __str__(self):
        return f"{self.group} | {self.date.strftime('%d.%m.%Y %H:%M')}"

    class Meta:
        ordering = ['date']
        verbose_name = "Учебное занятие"
        verbose_name_plural = "Учебные занятия"


class Student(TimeStampedFlagsModel):
    full_name = models.CharField(
        max_length=255,
        verbose_name="ФИО"
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Номер телефона"
    )
    parent_phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Номер телефона родителя"
    )
    birthday_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата рождения"
    )
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        verbose_name="Пол"
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name="Примечание"
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Баланс"
    )
    avatar = models.ImageField(
        upload_to='uploads/students/avatars/',
        blank=True,
        null=True,
        verbose_name='Аватарка'
    )
    department = models.CharField(
        max_length=50,
        choices=DepartmentChoices.choices,
        default=DepartmentChoices.KINDERGARTEN,
        verbose_name="Отдел"
    )
    account_number = models.IntegerField(
        blank=True,
        null=True,
        unique=True,
        verbose_name="Лицевой счет"
    )
    marked_for_delete = models.BooleanField(
        default=False,
        verbose_name="Помечен на удаление"
    )

    objects = StudentQuerySet.as_manager()

    def __str__(self):
        return f"{self.full_name}"

    class Meta:
        ordering = ['-id']
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"


class StudentToGroup(models.Model):
    group = models.ForeignKey(
        'students.StudyGroup',
        on_delete=models.CASCADE,
        related_name="students",
        verbose_name="Группа"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name="groups",
        verbose_name="Студент"
    )
    joined_date = models.DateField(
        default=timezone.now,
        verbose_name="Дата зачисления"
    )


class StudentVisit(models.Model):
    lesson = models.ForeignKey(
        'students.StudyLesson',
        on_delete=models.CASCADE,
        related_name="student_visits",
        verbose_name="Занятие"
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name="lesson_visits",
        verbose_name="Студент"
    )

    def __str__(self):
        return f"Посещение | {self.lesson} | {self.student}"

    class Meta:
        ordering = ['id']
        verbose_name = "Посещение занятия"
        verbose_name_plural = "Посещения занятий"


class StudentTransaction(FlagsModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Студент"
    )
    group = models.ForeignKey(
        'students.StudyGroup',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Группа"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Сумма"
    )
    transaction_date = models.DateField(
        verbose_name="Дата начисления"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    def __str__(self):
        return f"{self.student} | {self.amount}"

    class Meta:
        ordering = ['-transaction_date']
        verbose_name = "Транзакция с балансом"
        verbose_name_plural = "Транзакции с балансом"


class StudentBalanceAdjustment(TimeStampedModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='balance_adjustments',
        verbose_name="Студент"
    )
    old_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Старый баланс"
    )
    new_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Новый баланс"
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарий"
    )
    marked_for_delete = models.BooleanField(
        default=False,
        verbose_name="Помечен на удаление"
    )

    @cached_property
    def balance_diff(self):
        return self.new_balance - self.old_balance

    def __str__(self):
        return f"{self.student} | {self.old_balance} -> {self.new_balance} | {self.created_at.strftime('%d.%m.%Y')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Изменение баланса"
        verbose_name_plural = "Изменения баланса"


class StudentBonus(TimeStampedFlagsModel):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='bonuses',
        verbose_name="Студент"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Сумма"
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарий"
    )
    marked_for_delete = models.BooleanField(
        default=False,
        verbose_name="Помечен на удаление"
    )

    def __str__(self):
        return f"{self.student} | {self.amount} | {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Бонус студенту"
        verbose_name_plural = "Бонусы студенту"
