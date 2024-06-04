from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'is_staff', 'is_active', 'date_joined', 'last_updated']
    list_filter = ['is_staff', 'is_active']
    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'first_name', 'last_name', 'department','image')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active', 'first_name', 'last_name', 'department', 'image', 'description')}
        ),
    )
    search_fields = ['email', 'first_name', 'last_name', 'department']
    ordering = ['email']

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

admin.site.register(User, CustomUserAdmin)
