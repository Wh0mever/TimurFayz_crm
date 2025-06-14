from rest_framework import serializers

from base.serializers import DynamicFieldsModelSerializer
from payment.models import Payment, OutlayCategory, OutlayItem, Cash
from students.serializers import StudentSerializer
from user.serializers import UserSerializer


class OutlayCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OutlayCategory
        fields = ('id', 'title', 'department')


class OutlayItemSerializer(DynamicFieldsModelSerializer):
    category_obj = OutlayCategorySerializer(source='category', read_only=True)

    class Meta:
        model = OutlayItem
        fields = ('id', 'title', 'category', 'category_obj')
        read_only_fields = ('category_obj',)


class PaymentSerializer(serializers.ModelSerializer):
    created_user = UserSerializer(read_only=True)
    student_obj = StudentSerializer(
        source='student',
        fields=('id', 'full_name', 'balance', 'phone_number', 'account_number'),
        read_only=True
    )
    outlay_obj = OutlayItemSerializer(source='outlay', read_only=True, exclude=('category', 'category_obj'))
    department = serializers.CharField(read_only=True, default=None)

    class Meta:
        model = Payment
        fields = (
            'id',
            'payment_type',
            'payment_method',
            'payment_model_type',
            'student',
            'student_obj',
            'outlay',
            'outlay_obj',
            'amount',
            'payment_date',
            'created_at',
            'created_user',
            'marked_for_delete',
            'student_balance_after',
            'department',
            'comment'
        )

    def validate(self, attrs):
        if attrs.get('student') and attrs.get('outlay'):
            raise serializers.ValidationError("Нельзя указать одновременно студента и прочий расход")
        return attrs


class PaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'marked_for_delete')


class CashSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cash
        fields = ('id', 'payment_method', 'amount')


class PaymentSummaryByMethodSerializer(serializers.Serializer):
    payment_method = serializers.CharField()
    total_count = serializers.IntegerField(default=0)
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_outcome = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)


class PaymentSummarySerializer(serializers.Serializer):
    total_count = serializers.IntegerField(default=0)
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_outcome = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_methods = PaymentSummaryByMethodSerializer(many=True, required=False)
