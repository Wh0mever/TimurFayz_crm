from drf_extra_fields.fields import Base64ImageField
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from base.serializers import DynamicFieldsSerializerMixin
from students.models import StudyGroup, StudyLesson, Student, StudyGroupDay, StudentVisit, StudentBalanceAdjustment, \
    StudentTransaction, StudentBonus
from user.serializers import UserSerializer, WorkerSerializer


class StudentBalanceAdjustmentSerializer(serializers.ModelSerializer):
    created_user = UserSerializer(read_only=True)
    student_name = serializers.CharField(source='student.full_name', max_length=255, read_only=True)

    class Meta:
        model = StudentBalanceAdjustment
        fields = ('id', 'student', 'student_name', 'old_balance', 'new_balance', 'created_at', 'created_user',
                  'marked_for_delete', 'comment')
        read_only_fields = ('id', 'created_user', 'student_name', 'created_at', 'old_balance')


class StudentBalanceAdjustmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentBalanceAdjustment
        fields = ('id', 'marked_for_delete', 'comment')


class StudyGroupDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyGroupDay
        fields = ('id', 'day_of_week', 'start_time')


class StudyGroupSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    teacher_obj = WorkerSerializer(source='teacher', read_only=True)

    class Meta:
        model = StudyGroup
        fields = (
            'id',
            'name',
            'start_date',
            'end_date',
            'price',
            'teacher',
            'teacher_obj',
            'department',
            'marked_for_delete',
            'student_ids',
        )

    def validate_student_ids(self, value):
        for student_id in value:
            if not Student.objects.filter(id=student_id).exists():
                raise serializers.ValidationError(f"Student with ID {student_id} does not exist.")

        return value


class StudyLessonSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    group = StudyGroupSerializer(exclude=('student_ids',))

    class Meta:
        model = StudyLesson
        fields = (
            'id',
            'group',
            'date',
        )


class StudyGroupUpdateSerializer(serializers.ModelSerializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    joined_date = serializers.DateField(required=False)

    class Meta:
        model = StudyGroup
        fields = (
            'id',
            'name',
            'price',
            'start_date',
            'end_date',
            'teacher',
            'department',
            'marked_for_delete',
            'student_ids',
            'joined_date'
        )

    # def validate(self, attrs):
    #     if attrs.get('student_ids') and not attrs.get('joined_date'):
    #         raise serializers.ValidationError({'joined_date': "Обязательное поле"})
    #     return attrs

    def validate_joined_date(self, value):
        if value:
            if value > self.instance.end_date or value < self.instance.start_date:
                raise serializers.ValidationError({'joined_date': "Дата должна быть в пределах даты обучения группы"})
        return value

    def validate_student_ids(self, value):
        for student_id in value:
            if not Student.objects.filter(id=student_id).exists():
                raise serializers.ValidationError(f"Student with ID {student_id} does not exist.")

        return value


class StudentSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    avatar_upload = Base64ImageField(source='avatar', write_only=True, required=False)
    # group_ids = serializers.ListField(
    #     child=serializers.IntegerField(), write_only=True, required=False
    # )
    group_names = serializers.SerializerMethodField(read_only=True)

    group = serializers.PrimaryKeyRelatedField(queryset=StudyGroup.objects.all(), required=False)
    joined_date = serializers.DateField(required=False)

    class Meta:
        model = Student
        fields = (
            'id',
            'full_name',
            'gender',
            'phone_number',
            'parent_phone_number',
            'birthday_date',
            'comment',
            'balance',
            'account_number',
            'department',
            'avatar',
            'avatar_upload',
            'marked_for_delete',
            'group',
            'joined_date',
            'group_names',
        )
        read_only_fields = ('balance', 'avatar')

    def validate(self, attrs):
        group = attrs.get('group')
        joined_date = attrs.get('joined_date')
        if group:
            if not joined_date:
                raise serializers.ValidationError({'joined_date': "Обязательно поле"})
            if joined_date < group.start_date or joined_date > group.end_date:
                raise serializers.ValidationError({'joined_date': "Дата должна быть в пределах даты обучения группы"})
        return attrs

    # def validate_group_ids(self, value):
    #     for group_id in value:
    #         if not StudyGroup.objects.filter(id=group_id).exists():
    #             raise serializers.ValidationError(f"Group with ID {group_id} does not exist.")
    #
    #     return value

    def get_group_names(self, obj: Student):
        groups = obj.groups.values_list('group__name', flat=True)
        return groups


class StudyGroupDetailSerializer(serializers.ModelSerializer):
    # lessons = StudyLessonSerializer(exclude=('group',), many=True, read_only=True)
    students = serializers.SerializerMethodField(read_only=True)
    teacher_obj = WorkerSerializer(source='teacher', read_only=True)

    class Meta:
        model = StudyGroup
        fields = (
            'id',
            'name',
            'start_date',
            'end_date',
            'price',
            'teacher',
            'teacher_obj',
            'students',
        )

    @extend_schema_field(
        field=StudentSerializer(many=True)
    )
    def get_students(self, obj: StudyGroup):
        students = Student.objects.get_available().filter(groups__in=obj.students.all())
        return StudentSerializer(instance=students, many=True).data


class StudentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = (
            'id',
            'full_name',
            'department',
            'gender',
            'phone_number',
            'parent_phone_number',
            'birthday_date',
            'comment',
            'balance',
            'account_number',
            'marked_for_delete',
            'avatar',
        )


class StudentTransactionSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    student_obj = StudentSerializer(
        source='student',
        read_only=True,
        fields=('id', 'full_name', 'balance', 'phone_number', 'parent_phone_number')
    )
    group_obj = StudyGroupSerializer(source='group', read_only=True, fields=('id', 'name'))

    class Meta:
        model = StudentTransaction
        fields = ('id', 'student', 'student_obj', 'group', 'group_obj', 'amount', 'transaction_date')


class StudentBonusSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = StudentBonus
        fields = ('id', 'student', 'amount', 'comment', 'created_at', 'created_user', 'marked_for_delete')
        read_only_fields = ('id', 'created_at', 'created_user')


class StudentBonusUpdateSerializer(DynamicFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = StudentBonus
        fields = ('id', 'comment', 'marked_for_delete')


class StudentVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentVisit
        fields = ('id', 'lesson', 'student')


class StudentBalanceReportSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateTimeField()
    total = serializers.DecimalField(max_digits=15, decimal_places=2)
    reason = serializers.CharField(max_length=50)
    balance_change_type = serializers.CharField(max_length=50)
    balance_before = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance_after = serializers.DecimalField(max_digits=15, decimal_places=2)
    mark_for_delete = serializers.BooleanField(default=False)
    comment_text = serializers.CharField(default="")


class StudentIdListSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
