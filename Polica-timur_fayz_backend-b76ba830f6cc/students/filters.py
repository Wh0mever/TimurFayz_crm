from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters

from students.enums import DepartmentChoices
from students.models import StudyGroup, Student, StudyLesson, StudentTransaction, StudentBonus
from user.enums import UserType
from user.models import Worker

User = get_user_model()


class StudentFilter(filters.FilterSet):
    group = filters.ModelMultipleChoiceFilter(
        queryset=StudyGroup.objects.all(),
        method='by_group',
    )
    has_debt = filters.BooleanFilter(
        method='by_has_debt',
    )
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        method='by_department',
    )
    teacher = filters.ModelMultipleChoiceFilter(
        queryset=Worker.objects.filter(user__user_type=UserType.TEACHER),
        method='by_teacher'
    )
    has_bonus = filters.BooleanFilter(
        method='by_has_bonus'
    )
    bonus_start_date = filters.DateTimeFilter(
        method='by_bonus_start_date'
    )
    bonus_end_date = filters.DateTimeFilter(
        method='by_bonus_end_date'
    )

    class Meta:
        model = Student
        fields = ('birthday_date', 'gender', 'is_active', 'marked_for_delete',)

    def by_group(self, queryset, name, value):
        if value:
            queryset = queryset.filter(groups__group_id__in=value).distinct()
        return queryset

    def by_has_debt(self, queryset, name, value):
        if value:
            queryset = queryset.filter(balance__lt=0)
        else:
            queryset = queryset.filter(balance__gte=0)
        return queryset

    def by_teacher(self, queryset, name, value):
        if value:
            return queryset.filter(groups__group__teacher__in=value).distinct()
        return queryset

    def by_department(self, queryset, name, value):
        if value:
            queryset = queryset.filter(department__in=value)
        return queryset

    def by_has_bonus(self, queryset, name, value):
        if value is None or value == '':
            return queryset

        if value:
            return queryset.filter(Exists(StudentBonus.objects.filter(student=OuterRef('pk'))))

        return queryset

    def by_bonus_start_date(self, queryset, name, value):
        if value:
            return queryset.filter(bonuses__created_at__gte=value).distinct()
        return queryset

    def by_bonus_end_date(self, queryset, name, value):
        if value:
            return queryset.filter(bonuses__created_at__lte=value).distinct()
        return queryset


class StudyGroupFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(
        method="by_start_date"
    )
    end_date = filters.DateTimeFilter(
        method="by_end_date"
    )
    student = filters.ModelMultipleChoiceFilter(
        queryset=Student.objects.all(),
        method='by_student'
    )
    department = filters.MultipleChoiceFilter(
        choices=DepartmentChoices.choices,
        method='by_department'
    )
    teacher = filters.ModelMultipleChoiceFilter(
        queryset=Worker.objects.filter(user__user_type=UserType.TEACHER),
        field_name='teacher'
    )

    class Meta:
        model = StudyGroup
        fields = ['is_active', 'marked_for_delete', ]

    def by_start_date(self, queryset, name, value):
        queryset = queryset.filter(end_date__gte=value)
        return queryset

    def by_end_date(self, queryset, name, value):
        queryset = queryset.filter(start_date__lte=value)
        return queryset

    def by_student(self, queryset, name, value):
        if value:
            queryset = queryset.filter(students__student__in=value).distinct()
        return queryset

    def by_department(self, queryset, name, value):
        if value:
            queryset = queryset.filter(department__in=value)
        return queryset


class StudyLessonFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(
        field_name="date",
        lookup_expr="gte"
    )
    end_date = filters.DateTimeFilter(
        field_name="date",
        lookup_expr="lte"
    )
    group = filters.ModelMultipleChoiceFilter(
        queryset=StudyGroup.objects.all(),
        field_name='group'
    )
    student = filters.ModelMultipleChoiceFilter(
        queryset=Student.objects.all(),
        method='by_student'
    )

    class Meta:
        model = StudyLesson
        fields = ['group']

    def by_student(self, queryset, name, value):
        if value:
            queryset = queryset.filter(group__students__student__in=value).distinct()
        return queryset


class StudentTransactionFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(
        field_name="transaction_date",
        lookup_expr="gte"
    )
    end_date = filters.DateTimeFilter(
        field_name="transaction_date",
        lookup_expr="lte"
    )
    student = filters.ModelMultipleChoiceFilter(
        queryset=Student.objects.all(),
        method='by_student'
    )
    group = filters.ModelMultipleChoiceFilter(
        queryset=StudyGroup.objects.all(),
        method='by_group'
    )

    class Meta:
        model = StudentTransaction
        fields = ['student', 'group']

    def by_student(self, queryset, name, value):
        if value:
            queryset = queryset.filter(student__in=value).distinct()
        return queryset

    def by_group(self, queryset, name, value):
        if value:
            queryset = queryset.filter(group__in=value).distinct()
        return queryset


class StudentBonusFilter(filters.FilterSet):
    student = filters.ModelMultipleChoiceFilter(
        queryset=Student.objects.all(),
        field_name='student'
    )
    created_user = filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        field_name='created_user'
    )

    class Meta:
        model = StudentBonus
        fields = ['student', 'created_user', 'marked_for_delete', ]
