import django_filters.rest_framework as filters
from django.db.models import Q

from payment.enums import PaymentTypeChoices, PaymentMethodChoices
from payment.models import Payment, OutlayItem, OutlayCategory
from students.enums import DepartmentChoices
from students.models import Student


class PaymentFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    end_date = filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    payment_type = filters.MultipleChoiceFilter(
        choices=PaymentTypeChoices.choices,
        field_name='payment_type'
    )
    payment_method = filters.MultipleChoiceFilter(
        choices=PaymentMethodChoices.choices,
        field_name='payment_method'
    )
    student = filters.ModelMultipleChoiceFilter(
        queryset=Student.objects.all(),
        field_name='student'
    )
    outlay = filters.ModelMultipleChoiceFilter(
        queryset=OutlayItem.objects.all(),
        field_name='outlay'
    )
    outlay_category = filters.ModelMultipleChoiceFilter(
        queryset=OutlayCategory.objects.all(),
        field_name='outlay__category'
    )
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        method='by_department'
    )

    class Meta:
        model = Payment
        fields = ('payment_type', 'payment_method', 'student', 'outlay', 'marked_for_delete', 'payment_model_type')

    def by_department(self, queryset, name, value):
        if value:
            queryset = queryset.filter(
                Q(student__groups__group__department__in=value)
                | Q(outlay__category__department__in=value)
            ).distinct()
        return queryset


class OutlayCategoryFilter(filters.FilterSet):
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        field_name='department'
    )

    class Meta:
        model = OutlayCategory
        fields = ('department',)


class OutlayItemFilter(filters.FilterSet):
    category = filters.ModelMultipleChoiceFilter(
        queryset=OutlayCategory.objects.all(),
        field_name='category'
    )
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        field_name='category__department'
    )

    class Meta:
        model = OutlayItem
        fields = ('category', 'department')
