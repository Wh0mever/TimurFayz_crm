from django.db import transaction
from django.db.models import Count, Sum, DecimalField, Q, Case, When, F
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from base.api_views import MultiSerializerViewSetMixin, CustomPagination, DestroyFlagsViewSetMixin
from payment.enums import PaymentMethodChoices, PaymentTypeChoices
from payment.filters import PaymentFilter, OutlayItemFilter, OutlayCategoryFilter
from payment.models import Payment, OutlayCategory, OutlayItem, Cash
from payment.serializers import PaymentSerializer, OutlayCategorySerializer, OutlayItemSerializer, CashSerializer, \
    PaymentSummarySerializer, PaymentUpdateSerializer
from payment.services import create_payment, process_payment_delete


class PaymentViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = Payment.objects.get_available()
    serializer_action_classes = {
        'list': PaymentSerializer,
        'retrieve': PaymentSerializer,
        'create': PaymentSerializer,
        'partial_update': PaymentUpdateSerializer,
        'get_summary': PaymentSummarySerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
    ]
    filterset_class = PaymentFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = create_payment(**serializer.validated_data, created_user=request.user)
        serializer.instance = payment
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with transaction.atomic():
            process_payment_delete(instance)
            super().destroy(request, *args, **kwargs)
        return Response(status=204)

    def get_summary(self, request, *args, **kwargs):
        payments = self.filter_queryset(self.get_queryset())
        summary_data = payments.aggregate(
            total_count=Count('id'),
            total_income=Sum('amount', default=0, filter=Q(payment_type=PaymentTypeChoices.INCOME)),
            total_outcome=Sum('amount', default=0, filter=Q(payment_type=PaymentTypeChoices.OUTCOME)),
            total_amount=Sum(
                Case(
                    When(payment_type=PaymentTypeChoices.OUTCOME, then=-F('amount')),
                    default=F('amount')
                ), default=0)
        )

        payment_methods_summary = (
            payments.values('payment_method')
            .annotate(
                total_count=Count('id'),
                total_income=Sum('amount', default=0, filter=Q(payment_type=PaymentTypeChoices.INCOME)),
                total_outcome=Sum('amount', default=0, filter=Q(payment_type=PaymentTypeChoices.OUTCOME)),
                total_amount=Sum(
                    Case(
                        When(payment_type=PaymentTypeChoices.OUTCOME, then=-F('amount')),
                        default=F('amount')
                    ), default=0)
            ).order_by('-total_amount')
        )

        payment_methods_summary = [
            {
                'payment_method': dict(PaymentMethodChoices.choices).get(item['payment_method'], 'Unknown'),
                'total_count': item['total_count'],
                'total_income': item['total_income'],
                'total_outcome': item['total_outcome'],
                'total_amount': item['total_amount']
            }
            for item in payment_methods_summary
        ]

        summary_data['payment_methods'] = payment_methods_summary
        serializer = self.get_serializer(summary_data)
        return Response(serializer.data)


class OutlayCategoryViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = OutlayCategory.objects.get_available()
    serializer_action_classes = {
        'list': OutlayCategorySerializer,
        'retrieve': OutlayCategorySerializer,
        'create': OutlayCategorySerializer,
        'partial_update': OutlayCategorySerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    search_fields = ['title']
    filterset_class = OutlayCategoryFilter


class OutlayItemViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = OutlayItem.objects.get_available()
    serializer_action_classes = {
        'list': OutlayItemSerializer,
        'retrieve': OutlayItemSerializer,
        'create': OutlayItemSerializer,
        'partial_update': OutlayItemSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]
    search_fields = ['title']
    filterset_class = OutlayItemFilter


class CashViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Cash.objects.all()
    serializer_action_classes = {
        'list': CashSerializer,
        'retrieve': CashSerializer,
    }
