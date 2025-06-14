import os

from django.db import models
from django.contrib.auth import get_user_model

from base.managers import FlagsQuerySet, DeleteFlagQuerySet, ActiveFlagQuerySet


class FileCleanupMixin:
    def delete_old_file(self, field):
        old_file = getattr(self.__class__.objects.get(pk=self.pk), field.name)
        new_file = getattr(self, field.name)
        if old_file and old_file != new_file:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)

    def delete_files_on_delete(self):
        for field in self._meta.fields:
            if isinstance(field, (models.FileField, models.ImageField)):
                file = getattr(self, field.name)
                if file and os.path.isfile(file.path):
                    os.remove(file.path)

    def save(self, *args, **kwargs):
        if self.pk:
            for field in self._meta.fields:
                if isinstance(field, (models.FileField, models.ImageField)):
                    self.delete_old_file(field)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.delete_files_on_delete()
        super().delete(*args, **kwargs)


class TimeStampedModel(models.Model):
    """
    Models that have "created_at" and "created_user" fields
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан',
    )
    created_user = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_%(class)s_set',
        verbose_name='Создал'
    )

    # updated_at = models.DateTimeField(verbose_name='Обновлен', auto_now=True)

    class Meta:
        abstract = True


class DeleteFlagModel(models.Model):
    is_deleted = models.BooleanField(verbose_name='Удален', default=False)
    deleted_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="Дата удаления"
    )
    deleted_user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Удалил"
    )

    objects = DeleteFlagQuerySet.as_manager()
    query_set_class = DeleteFlagQuerySet

    class Meta:
        abstract = True


class ActiveFlagModel(models.Model):
    is_active = models.BooleanField(verbose_name='Активен', default=True)

    objects = ActiveFlagQuerySet.as_manager()
    query_set_class = ActiveFlagQuerySet

    class Meta:
        abstract = True


class FlagsModel(models.Model):
    """
    Models that have active and deleted flags fields
    """
    is_active = models.BooleanField(verbose_name='Активен', default=True)
    is_deleted = models.BooleanField(verbose_name='Удален', default=False)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата удаления"
    )
    deleted_user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='deleted_%(class)s_set',
        verbose_name="Удалил"
    )

    objects = FlagsQuerySet.as_manager()
    query_set_class = FlagsQuerySet

    class Meta:
        abstract = True

    def is_available(self):
        return (not self.is_deleted) and self.is_active


class TimeStampedFlagsModel(FlagsModel, TimeStampedModel):
    class Meta:
        abstract = True
