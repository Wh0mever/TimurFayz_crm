import filetype

from drf_extra_fields.fields import Base64FileField
from rest_framework import serializers


class DynamicFieldsSerializerMixin:

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            not_allowed = set(exclude)
            for field_name in not_allowed:
                self.fields.pop(field_name)


class DynamicFieldsModelSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    pass
