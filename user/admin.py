from django.contrib import admin
from django.contrib.auth import admin as user_admin

from user.models import User


@admin.register(User)
class UserAdmin(user_admin.UserAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'is_active']
    list_display_links = ['id', 'username']
    fieldsets = [
        (
            'Credentials',
            {
                "fields": ["username", "password"]
            }
        ),
        (
            'Personal Data',
            {
                "fields": ["first_name", "last_name", "avatar", "user_type"]
            }
        ),
        (
            "User system data",
            {
                "fields": ["groups", "user_permissions", "is_superuser", "is_staff", "is_active"]
            }
        )
    ]
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
