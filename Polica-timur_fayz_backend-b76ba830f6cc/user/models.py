from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django_resized import ResizedImageField

from students.enums import DepartmentChoices
from user.enums import UserType


class MyUserManager(BaseUserManager):
    """
    A custom user manager to deal with emails as unique identifiers for auth
    instead of usernames. The default that's used is "UserManager"
    """

    def create_user(self, username, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

    def _create_user(self, username, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        user = self.model(username=username, **extra_fields)
        user.is_active = True
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Фамилия"
    )
    user_type = models.CharField(
        max_length=100,
        choices=UserType.choices,
        default=UserType.ADMIN,
        verbose_name="Роль"
    )
    username = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Логин"
    )
    avatar = ResizedImageField(
        upload_to="users/avatars/",
        size=[400, 400],
        crop=['middle', 'center'],
        blank=True,
        null=True,
        verbose_name="Фото пользователя"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Статус персонала"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активный"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    USERNAME_FIELD = 'username'
    objects = MyUserManager()

    class Meta:
        ordering = ['-id']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.get_full_name()}"

    def save(self, *args, **kwargs):
        if self.id:
            old_instance: User = User.objects.get(pk=self.id)
            if self.avatar and self.avatar != old_instance.avatar:
                old_instance.avatar.delete()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        return self.first_name


class Worker(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="worker",
        verbose_name="Пользователь"
    )
    salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Зарплата"
    )
    department = models.CharField(
        max_length=50,
        choices=DepartmentChoices.choices,
        default=DepartmentChoices.SCHOOL,
        null=True,
        blank=True,
        verbose_name="Отдел"
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        ordering = ['id']
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
