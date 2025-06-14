from collections import OrderedDict

from django.utils import timezone
from rest_framework import viewsets, pagination
from rest_framework.response import Response


class MultiSerializerViewSetMixin:
    serializer_action_classes = {}

    def get_serializer_class(self):
        serializer = self.serializer_action_classes.get(self.action)
        if not serializer:
            serializer = super().get_serializer_class()
        return serializer


class DestroyFlagsViewSetMixin:

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.is_active = False
        obj.deleted_user = request.user
        obj.deleted_at = timezone.now()
        obj.save()
        return Response(status=204)


class CustomPagination(pagination.PageNumberPagination):
    page_size = 20

    def paginate_queryset(self, queryset, request, view=None):
        paginate = bool(request.query_params.get('page', None))
        if paginate:
            return super().paginate_queryset(queryset, request, view)
        return None

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))
