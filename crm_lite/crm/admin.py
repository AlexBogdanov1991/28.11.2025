from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Company, Storage, Supplier, Product, Supply, SupplyProduct


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


class StorageInline(admin.StackedInline):
    model = Storage
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'created_at', 'owner_info')
    search_fields = ('name', 'inn')
    list_filter = ('created_at',)
    inlines = [StorageInline]

    def owner_info(self, obj):
        owner = obj.user_set.filter(is_company_owner=True).first()
        if owner:
            return f"{owner.get_full_name()} ({owner.email})"
        return "Нет владельца"

    owner_info.short_description = 'Владелец'


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('company', 'address', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('company__name', 'address')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'company', 'contact_person', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('name', 'inn', 'company__name', 'contact_person')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'quantity', 'purchase_price', 'sale_price',
                    'storage', 'is_active', 'created_at')
    list_filter = ('storage__company', 'is_active', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('quantity', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('storage', 'name', 'sku', 'description')}),
        ('Цены', {'fields': ('purchase_price', 'sale_price')}),
        ('Статистика', {'fields': ('quantity', 'is_active', 'created_at', 'updated_at')}),
    )


class SupplyProductInline(admin.TabularInline):
    model = SupplyProduct
    extra = 1
    readonly_fields = ('total_cost',)

    def total_cost(self, obj):
        if obj.id:
            return obj.total_cost()
        return "—"

    total_cost.short_description = 'Общая стоимость'


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'delivery_date', 'invoice_number',
                    'created_by', 'total_cost_display', 'created_at')
    list_filter = ('supplier__company', 'delivery_date', 'created_at')
    search_fields = ('supplier__name', 'invoice_number', 'created_by__email')
    inlines = [SupplyProductInline]
    readonly_fields = ('created_by', 'created_at')

    def total_cost_display(self, obj):
        return f"{obj.total_cost():.2f} руб."

    total_cost_display.short_description = 'Общая стоимость'

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SupplyProduct)
class SupplyProductAdmin(admin.ModelAdmin):
    list_display = ('supply', 'product', 'quantity', 'purchase_price', 'total_cost')
    list_filter = ('supply__supplier__company', 'supply__delivery_date')
    search_fields = ('product__name', 'product__sku', 'supply__invoice_number')

    def total_cost(self, obj):
        return obj.total_cost()
    total_cost.short_description = 'Общая стоимость'