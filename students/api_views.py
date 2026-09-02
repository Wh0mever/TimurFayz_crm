from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch, Subquery, OuterRef
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiRequest
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone

from base.api_views import MultiSerializerViewSetMixin, CustomPagination, DestroyFlagsViewSetMixin
from base.sms_service import SMSService
from students.enums import Gender, DaysOfWeek
from students.exception import StudyGroupDayAlreadyExists
from students.filters import StudyGroupFilter, StudyLessonFilter, StudentFilter, StudentTransactionFilter, \
    StudentBonusFilter
from students.models import Student, StudyGroup, StudentToGroup, StudyLesson, StudentVisit, StudentBalanceAdjustment, \
    StudentTransaction, StudentBonus
from students.serializers import StudentSerializer, StudyGroupSerializer, StudyGroupDetailSerializer, \
    StudyLessonSerializer, StudyGroupUpdateSerializer, StudyGroupDaySerializer, StudentVisitSerializer, \
    StudentBalanceAdjustmentSerializer, StudentTransactionSerializer, StudentBonusSerializer, \
    StudentBalanceReportSerializer, StudentBonusUpdateSerializer, StudentBalanceAdjustmentUpdateSerializer, \
    StudentIdListSerializer, StudentTransferToGroupSerializer, StudentMassTransferSerializer, \
    StudentIdsRequiredSerializer
from students.services import add_students_to_group, update_group_students_list, \
    create_group_lessons_by_study_day, create_student_visit, delete_student_visit, \
    delete_group_lessons_by_study_date, update_study_day, increase_student_balance, decrease_student_balance, \
    add_student_to_groups, create_student_bonus, handle_student_bonus_delete, \
    get_student_debit_credit_report, recalculate_group_transactions, generate_student_account_number, \
    transfer_student_to_group, mass_transfer_students, mass_delete_students, mass_restore_students, \
    MassOperationBackupError
from user.enums import UserType


class StudentViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = Student.objects.get_available()
    serializer_action_classes = {
        'list': StudentSerializer,
        'retrieve': StudentSerializer,
        'create': StudentSerializer,
        'partial_update': StudentSerializer,
        'get_student_balance_report': StudentBalanceReportSerializer,
        'transfer_student_to_group': StudentTransferToGroupSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    search_fields = ['full_name', 'phone_number', 'parent_phone_number', 'comment']
    filterset_class = StudentFilter
    ordering_fields = ['full_name', 'gender', 'balance']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        qs = qs.prefetch_related('groups__group')

        if user.user_type in [UserType.TEACHER]:
            if user.worker:
                qs = qs.filter(groups__group__teacher=user.worker).distinct()

        group_filter = self.request.query_params.get('group')
        if group_filter:
            qs = qs.annotate(
                joined_date=Subquery(
                    StudentToGroup.objects.filter(student_id=OuterRef('pk'), group_id=group_filter)
                    .values('joined_date')[:1]
                )
            )

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        group = validated_data.pop('group', None)
        date_joined = validated_data.pop('joined_date', None)
        account_number = validated_data.pop('account_number')
        with transaction.atomic():
            account_number = generate_student_account_number() if not account_number else account_number
            student = serializer.save(created_user=request.user, account_number=account_number)
            if group:
                add_student_to_groups(student, [group.id], date_joined)
        return Response(serializer.data, status=201)

    def partial_update(self, request, *args, **kwargs):
        student = self.get_object()
        serializer = self.get_serializer(instance=student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # group_ids = serializer.validated_data.pop('group_ids', None)
        # if group_ids is not None:
        #     update_student_groups_list(student, group_ids)
        serializer.save()
        return Response(serializer.data)

    def get_student_balance_report(self, request, *args, **kwargs):
        student = self.get_object()
        transactions = get_student_debit_credit_report(student)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)

    def transfer_student_to_group(self, request, *args, **kwargs):
        student = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        transfer_student_to_group(
            student=student,
            group_from=validated_data.get('group_from'),
            group_to=validated_data.get('group_to'),
            joined_date=validated_data.get('joined_date'),
        )
        return Response({'success': True})

    def get_create_options(self, request, *args, **kwargs):
        gender_options = [{'value': option[0], 'label': option[1]} for option in Gender.choices]
        return Response(data={
            'gender_options': gender_options,
        })
    
    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.is_active = False
        obj.deleted_user = request.user
        obj.deleted_at = timezone.now()
        obj.account_number = None
        obj.save()
        return Response(status=204)

class StudyGroupViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = StudyGroup.objects.get_available()
    serializer_action_classes = {
        'list': StudyGroupSerializer,
        'retrieve': StudyGroupDetailSerializer,
        'create': StudyGroupSerializer,
        'partial_update': StudyGroupUpdateSerializer,
        'add_study_day': StudyGroupDaySerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter
    ]
    search_fields = ['name']
    filterset_class = StudyGroupFilter
    ordering_fields = ['name']

    def get_queryset(self):
        user = self.request.user

        qs = super().get_queryset()
        qs = qs.select_related('teacher__user').prefetch_related(
            # 'lessons',
            # 'study_days',
            Prefetch('students', StudentToGroup.objects.select_related('student', 'group'))
        )

        if user.user_type in [UserType.TEACHER]:
            if user.worker:
                qs = qs.filter(teacher=user.worker)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_ids = serializer.validated_data.pop('student_ids', None)
        # study_days = serializer.validated_data.pop('study_days', None)

        with transaction.atomic():
            group = serializer.save(created_user=request.user)
            # create_study_days_for_group(group, study_days)
            # create_group_lessons(group)
            add_students_to_group(group, student_ids)
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            student_ids = serializer.validated_data.pop('student_ids', None)
            if student_ids is not None:
                joined_date = serializer.validated_data.pop('joined_date', None)
                joined_date = joined_date.date() if joined_date else None
                update_group_students_list(instance, student_ids, joined_date)

            current_start_date = instance.start_date
            current_end_date = instance.end_date

            instance = serializer.save()

            # if current_start_date != instance.start_date or current_end_date != instance.end_date:
            #     recalculate_group_transactions(instance)
        return Response(serializer.data)

    def add_study_day(self, request, *args, **kwargs):
        group: StudyGroup = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if group.study_days.filter(day_of_week=data['day_of_week']).exists():
            raise StudyGroupDayAlreadyExists
        with transaction.atomic():
            study_day = serializer.save(group=group)

            group.refresh_from_db(fields=['study_days'])
            create_group_lessons_by_study_day(group, study_day)
        return Response(serializer.data, status=201)

    def delete_study_day(self, request, *args, **kwargs):
        group: StudyGroup = self.get_object()
        study_day = group.study_days.get(pk=kwargs['study_day_id'])
        delete_group_lessons_by_study_date(study_day)
        return Response(status=204)

    def update_study_day(self, request, *args, **kwargs):
        group: StudyGroup = self.get_object()
        study_day = group.study_days.get(pk=kwargs['study_day_id'])
        serializer = self.get_serializer(instance=study_day, data=request.data)
        serializer.is_valid(raise_exception=True)
        start_time = serializer.validated_data.get('start_time')
        day_of_week = serializer.validated_data.get('day_of_week')
        update_study_day(study_day, start_time, day_of_week)
        return Response(serializer.data)

    def get_create_options(self, request, *args, **kwargs):
        weekday_options = [{'value': option[0], 'label': option[1]} for option in DaysOfWeek.choices]
        return Response(data={
            'weekday_options': weekday_options,
        })


class StudentTransactionViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = StudentTransaction.objects.get_available().select_related('student', 'group')
    serializer_action_classes = {
        'list': StudentTransactionSerializer,
        'retrieve': StudentTransactionSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter
    ]
    filterset_class = StudentTransactionFilter

    def destroy(self, request, *args, **kwargs):
        instance: StudentTransaction = self.get_object()
        increase_student_balance(instance.student.id, instance.amount)
        return super().destroy(request, *args, **kwargs)


class StudentBalanceAdjustmentViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = StudentBalanceAdjustment.objects.select_related('student', 'created_user')
    serializer_action_classes = {
        'list': StudentBalanceAdjustmentSerializer,
        'create': StudentBalanceAdjustmentSerializer,
        'retrieve': StudentBalanceAdjustmentSerializer,
        'partial_update': StudentBalanceAdjustmentUpdateSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter
    ]
    filterset_fields = ['student', 'marked_for_delete', ]
    search_fields = ['student__name']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            student = serializer.validated_data['student']
            instance: StudentBalanceAdjustment = serializer.save(created_user=request.user, old_balance=student.balance)
            increase_student_balance(student.id, instance.balance_diff)
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        instance: StudentBalanceAdjustment = self.get_object()
        with transaction.atomic():
            decrease_student_balance(instance.student.pk, instance.balance_diff)
            instance.delete()
        return Response(status=204)


class StudentBonusViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = StudentBonus.objects.get_available().select_related('student', 'created_user')
    serializer_action_classes = {
        'list': StudentBonusSerializer,
        'retrieve': StudentBonusSerializer,
        'create': StudentBonusSerializer,
        'partial_update': StudentBonusUpdateSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend
    ]
    filterset_class = StudentBonusFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        instance = create_student_bonus(**data, user=request.user)
        serializer.instance = instance
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        handle_student_bonus_delete(instance)
        return super().destroy(request, *args, **kwargs)


class StudyLessonViewSet(MultiSerializerViewSetMixin, DestroyFlagsViewSetMixin, ModelViewSet):
    queryset = StudyLesson.objects.filter(group__is_deleted=False)
    serializer_action_classes = {
        'list': StudyLessonSerializer,
        'retrieve': StudyLessonSerializer,
        'partial_update': StudyLessonSerializer
    }
    filter_backends = [
        DjangoFilterBackend,
    ]
    filterset_class = StudyLessonFilter

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.prefetch_related(
            Prefetch(
                'group', StudyGroup.objects.prefetch_related('students__student')
            )
        )
        return qs


class StudentVisitView(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = StudentVisit.objects.all()
    serializer_action_classes = {
        'list': StudentVisitSerializer,
        'retrieve': StudentVisitSerializer,
        'create': StudentVisitSerializer,
    }
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
    ]
    filterset_fields = ['lesson', 'student']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit_obj = create_student_visit(**serializer.validated_data)
        serializer.instance = visit_obj
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_student_visit(instance)
        return Response(status=204)


class SendSmsToDebtors(APIView):

    @extend_schema(request=StudentIdListSerializer())
    def post(self, request, *args, **kwargs):
        student_ids = request.data.get('student_ids', [])
        if student_ids:
            students = Student.objects.filter(id__in=student_ids)
            if not students.exists():
                return Response(data={'detail': "Не найдено ни одного студента"}, status=404)

            student_messages = [
                {
                    "phone_numbers": [num for num in [student.phone_number, student.parent_phone_number] if num],
                    "message": settings.DEBTOR_NOTIFY_SMS_TEMPLATE.format(abs(student.balance))
                }
                for student in students
            ]

            SMSService().send_mass_sms_with_individual_message(student_messages)

            return Response(data={'detail': "Сообщения успешно доставлены"}, status=200)


class MassTransferStudents(APIView):
    """Массовый перенос студентов между группами (перевод на следующий класс).

    dry_run=true — предпросмотр: те же расчёты (возврат старой группы,
    до-начисление новой), без записи в БД.
    """

    @extend_schema(request=StudentMassTransferSerializer())
    def post(self, request, *args, **kwargs):
        # Перенос доступен всем ролям (решение клиента, 2026-09-03) — как и
        # одиночный перевод. Массовое удаление при этом остаётся только у ADMIN.
        serializer = StudentMassTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = mass_transfer_students(**serializer.validated_data)
        except MassOperationBackupError as e:
            return Response(
                data={'detail': 'Не удалось создать бэкап — перенос отменён. %s' % e},
                status=500,
            )
        return Response(data=result, status=200)


class MassDeleteStudents(APIView):
    """Массовое мягкое удаление студентов (галочки в списке).

    account_number сохраняется — mass-restore возвращает студентов
    ровно в исходное состояние («Отмена» после удаления).
    """

    @extend_schema(request=StudentIdsRequiredSerializer())
    def post(self, request, *args, **kwargs):
        # Массовое удаление — ТОЛЬКО администратор (требование клиента).
        if request.user.user_type != UserType.ADMIN:
            return Response(
                data={'detail': 'Массовое удаление доступно только администратору'},
                status=403,
            )

        serializer = StudentIdsRequiredSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            deleted, backup_file = mass_delete_students(
                serializer.validated_data['student_ids'], user=request.user,
            )
        except MassOperationBackupError as e:
            return Response(
                data={'detail': 'Не удалось создать бэкап — удаление отменено. %s' % e},
                status=500,
            )
        return Response(
            data={'deleted': deleted, 'count': len(deleted), 'backup_file': backup_file},
            status=200,
        )


class MassRestoreStudents(APIView):
    """Отмена массового удаления: восстановление мягко удалённых студентов."""

    @extend_schema(request=StudentIdsRequiredSerializer())
    def post(self, request, *args, **kwargs):
        # Отмена массового удаления — ТОЛЬКО администратор (как и само удаление).
        if request.user.user_type != UserType.ADMIN:
            return Response(
                data={'detail': 'Восстановление доступно только администратору'},
                status=403,
            )

        serializer = StudentIdsRequiredSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            restored, backup_file = mass_restore_students(serializer.validated_data['student_ids'])
        except MassOperationBackupError as e:
            return Response(
                data={'detail': 'Не удалось создать бэкап — восстановление отменено. %s' % e},
                status=500,
            )
        return Response(
            data={'restored': restored, 'count': len(restored), 'backup_file': backup_file},
            status=200,
        )
