from django.contrib import admin
from user.models import ResUser, RoleDashboardMapping
# Register your models here.
admin.site.register(ResUser)
admin.site.register(RoleDashboardMapping)

# admin.site.register(PermissionGroup)
# admin.site.register(ResUserPermission)

# from django.contrib import admin
# from user.models import ResUser, ResUserPermission

# @admin.register(ResUser)
# class ResUserAdmin(admin.ModelAdmin):
#     """
#     Admin configuration for ResUser model.
#     """
#     list_display = (
#         'full_name', 'email_id', 'mobile_no', 'role', 'role_name',
#         'company_name', 'price_slab', 'status', 'dob', 'gender',
#         'created_at', 'updated_at'
#     )
#     search_fields = ('full_name', 'email_id', 'mobile_no', 'role', 'role_name')
#     list_filter = ('status', 'role', 'role_name', 'gender', 'created_at')
#     ordering = ('full_name', 'email_id')
#     readonly_fields = ('created_at', 'updated_at')

# @admin.register(ResUserPermission)
# class ResUserPermissionAdmin(admin.ModelAdmin):
#     """
#     Admin configuration for ResUserPermission model.
#     """
#     list_display = (
#         'user', 'view_only', 'copy', 'print_perm', 'download',
#         'share', 'screenshots', 'edit', 'delete', 'manage_roles',
#         'approve', 'reject', 'archive', 'restore', 'transfer',
#         'custom_access', 'full_control', 'view_perm',
#         'add_perm', 'update_perm', 'delete_perm', 'created_at', 'updated_at'
#     )
#     search_fields = ('user__full_name', 'user__email_id')
#     list_filter = ('view_only', 'edit', 'delete', 'full_control', 'created_at')
#     ordering = ('user', 'created_at')
#     readonly_fields = ('created_at', 'updated_at')

