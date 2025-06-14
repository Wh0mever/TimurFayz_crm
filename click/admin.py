from django.contrib import admin

from click.models import ClickTransaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'click_trans_id', 'merchant_trans_id', 'amount', 'action', 'status', 'sign_datetime')
    list_display_links = ('id',)
    list_filter = ('status',)
    search_fields = ['status', 'id', 'merchant_trans_id']


admin.site.register(ClickTransaction, TransactionAdmin)
