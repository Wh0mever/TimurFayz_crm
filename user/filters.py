from django_filters import rest_framework as filters

from django.contrib.auth import get_user_model

from students.enums import DepartmentChoices
from user.enums import UserType
from user.models import Worker

User = get_user_model()


class UserFilter(filters.FilterSet):
    user_type = filters.MultipleChoiceFilter(
        choices=UserType.choices,
        field_name='user_type'
    )

    class Meta:
        model = User
        fields = ('user_type',)


class WorkerFilter(filters.FilterSet):
    user_type = filters.MultipleChoiceFilter(
        choices=UserType.choices,
        method='by_user_type'
    )
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        method='by_department'
    )

    class Meta:
        model = Worker
        fields = ('department',)

    def by_user_type(self, queryset, name, value):
        if value:
            queryset = queryset.filter(user__user_type__in=value)
        return queryset

    def by_department(self, queryset, name, value):
        if value:
            queryset = queryset.filter(department__in=value)
        return queryset
