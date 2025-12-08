from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Storage, Supplier, Product, Supply, Sale


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'company', 'is_company_owner', 'is_staff')
    list_filter = ('is_company_owner', 'company', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Company info', {'fields': ('company', 'is_company_owner')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'created_at')
    search_fields = ('name', 'inn')
    list_filter = ('created_at',)


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('company', 'address', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('company__name', 'address')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'company', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('name', 'inn', 'company__name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'purchase_price', 'sale_price', 'storage', 'created_at')
    list_filter = ('storage__company', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('quantity',)


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'delivery_date', 'created_by', 'created_at')
    list_filter = ('supplier__company', 'delivery_date', 'created_at')
    search_fields = ('supplier__name', 'created_by__email')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('buyer_name', 'company', 'created_by', 'discount', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('buyer_name', 'company__name')