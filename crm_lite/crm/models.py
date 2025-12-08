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

    # Переопределяем поля для использования email как основного идентификатора
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"


class Company(models.Model):
    inn = models.CharField(
        max_length=12,
        unique=True,
        verbose_name='ИНН'
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Название компании'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'

    def __str__(self):
        return self.name


class Storage(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        verbose_name='Компания'
    )
    address = models.TextField(verbose_name='Адрес склада')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'

    def __str__(self):
        return f"Склад {self.company.name}"


class Supplier(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='Компания'
    )
    name = models.CharField(max_length=255, verbose_name='Название поставщика')
    inn = models.CharField(max_length=12, verbose_name='ИНН поставщика')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        unique_together = ['company', 'inn']

    def __str__(self):
        return self.name


class Product(models.Model):
    storage = models.ForeignKey(
        Storage,
        on_delete=models.CASCADE,
        verbose_name='Склад'
    )
    name = models.CharField(max_length=255, verbose_name='Название товара')
    description = models.TextField(blank=True, verbose_name='Описание товара')
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return f"{self.name} ({self.quantity} шт.)"


class Supply(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        verbose_name='Поставщик'
    )
    delivery_date = models.DateField(verbose_name='Дата поставки')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Создатель поставки'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'

    def __str__(self): return f"Поставка от {self.supplier.name} ({self.delivery_date})"

class SupplyProduct(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Товар в поставке'
        verbose_name_plural = 'Товары в поставках'
        unique_together = ['supply', 'product']

class Sale(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='Компания'
    )
    buyer_name = models.CharField(max_length=255, verbose_name='Имя покупателя')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Создатель продажи'
    )
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Скидка (%)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата продажи')

    class Meta:
        verbose_name = 'Продажа'
        verbose_name_plural = 'Продажи'

    def __str__(self):
        return f"Продажа #{self.id} - {self.buyer_name}"

class ProductSale(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Товар в продаже'
        verbose_name_plural = 'Товары в продажах'
        unique_together = ['sale', 'product']