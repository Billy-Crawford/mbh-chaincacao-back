from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'email', 'role', 'village', 'region']
    list_filter   = ['role']
    fieldsets     = UserAdmin.fieldsets + (
        ('Infos ChainCacao', {'fields': ('role', 'telephone', 'village', 'region', 'wallet_address')}),
    )