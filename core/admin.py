from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from core.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Admin configuration for the custom user model.
    """

    ordering = ('email',)
    list_display = (
        'email',
        'first_name',
        'last_name',
        'mobile_number',
        'is_email_verified',
        'is_staff',
        'is_active',
    )
    search_fields = ('email', 'first_name', 'last_name', 'mobile_number')

    fieldsets = (
        (None, {'fields': ('email', 'mobile_number', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name')}),
        ('Verification', {'fields': ('is_email_verified',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'mobile_number', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_superuser'),
            },
        ),
    )
