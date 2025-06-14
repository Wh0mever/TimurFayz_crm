from django.db.models import QuerySet


class DeleteFlagQuerySet(QuerySet):
    def get_available(self):
        return self.filter(is_deleted=False)


class ActiveFlagQuerySet(QuerySet):
    def get_active(self):
        return self.filter(is_active=True)


class FlagsQuerySet(QuerySet):

    def get_available(self):
        return self.filter(is_deleted=False, is_active=True)

    def get_active(self):
        return self.filter(is_active=True)