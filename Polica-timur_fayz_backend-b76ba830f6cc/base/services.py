from django.utils import timezone


def set_obj_deleted(obj, user):
    obj.is_deleted = True
    obj.is_active = False
    obj.deleted_user = user
    obj.deleted_at = timezone.now()
    obj.save()
