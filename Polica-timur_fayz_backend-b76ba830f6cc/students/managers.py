from django.db.models import QuerySet

from base.managers import FlagsQuerySet
from user.enums import UserType


class StudentGroupQuerySet(FlagsQuerySet):
    def by_user_department(self, user):
        if user.user_type in [UserType.TEACHER] and user.worker:
            return self.filter(department=user.worker.department)
        return self


class StudentQuerySet(FlagsQuerySet):
    def by_user_department(self, user):
        if user.user_type in [UserType.TEACHER] and user.worker:
            return self.filter(groups__group__department=user.worker.department).distinct()
        return self
