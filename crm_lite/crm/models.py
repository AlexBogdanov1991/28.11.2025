from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator


class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='Email')
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Компания'
    )
    is_company_owner = models.BooleanField(default=False, verbose_name='Владелец компании')

    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"


class Company(models.Model):
    inn = models.CharField(max_length=12, unique=True, verbose_name='ИНН')
    name = models.CharField(max_length=255, unique=True, verbose_name='Название компании')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'

    def __str__(self):
        return self.name


class Storage(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, verbose_name='Компания')
    address = models.TextField(verbose_name='Адрес склада')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'

    def __str__(self):
        return f"Склад {self.company.name}"


class Supplier(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Компания')
    name = models.CharField(max_length=255, verbose_name='Название поставщика')
    inn = models.CharField(max_length=12, verbose_name='ИНН поставщика')
    contact_person = models.CharField(max_length=255, blank=True, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        unique_together = ['company', 'inn']

    def __str__(self):
        return self.name


class Product(models.Model):
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE, verbose_name='Склад')
    name = models.CharField(max_length=255, verbose_name='Название товара')
    description = models.TextField(blank=True, verbose_name='Описание товара')
    sku = models.CharField(max_length=100, unique=True, verbose_name='Артикул')
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Количество на складе'
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Закупочная цена'
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена продажи'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (Арт: {self.sku})"


class Supply(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='Поставщик')
    delivery_date = models.DateField(verbose_name='Дата поставки')
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name='Номер накладной')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создатель поставки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    notes = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
        ordering = ['-delivery_date']

    def __str__(self):
        return f"Поставка #{self.id} от {self.supplier.name} ({self.delivery_date})"

    def total_cost(self):
        total = 0
        for item in self.supplyproduct_set.all():
            total += item.product.purchase_price * item.quantity
        return total

class SupplyProduct(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, verbose_name='Поставка')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Количество'
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена закупки'
    )

    class Meta:
        verbose_name = 'Товар в поставке'
        verbose_name_plural = 'Товары в поставках'
        unique_together = ['supply', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def total_cost(self):
        return self.purchase_price * self.quantity