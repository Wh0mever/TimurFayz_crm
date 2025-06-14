from django.contrib import admin

from payment.models import Payment, Cash


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'amount', 'payment_type', 'payment_model_type',
                    'is_active', 'is_deleted', 'deleted_user', 'marked_for_delete']


@admin.register(Cash)
class CashAdmin(admin.ModelAdmin):
    list_display = ['payment_method', 'amount']