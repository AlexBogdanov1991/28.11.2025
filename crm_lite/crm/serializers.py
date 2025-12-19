from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.db import transaction
from .models import User, Company, Storage, Supplier, Product, Supply, SupplyProduct


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные')
        else:
            raise serializers.ValidationError('Необходимо указать email и пароль')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'company', 'is_company_owner')
        read_only_fields = ('id', 'is_company_owner')


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ('id', 'inn', 'name', 'created_at', 'owner')
        read_only_fields = ('id', 'created_at', 'owner')

    def get_owner(self, obj):
        owner = obj.user_set.filter(is_company_owner=True).first()
        if owner:
            return f"{owner.get_full_name()} ({owner.email})"
        return None

    def validate_inn(self, value):
        if not value.isdigit() or len(value) not in [10, 12]:
            raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр")
        return value


class StorageSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Storage
        fields = ('id', 'company', 'company_name', 'address', 'created_at')
        read_only_fields = ('id', 'created_at')


class SupplierSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Supplier
        fields = ('id', 'company', 'company_name', 'name', 'inn', 'contact_person',
                  'phone', 'email', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_inn(self, value):
        if not value.isdigit() or len(value) not in [10, 12]:
            raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр")
        return value


class ProductSerializer(serializers.ModelSerializer):
    storage_company_name = serializers.CharField(source='storage.company.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'storage', 'storage_company_name', 'name', 'description', 'sku',
                  'quantity', 'purchase_price', 'sale_price', 'is_active',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'quantity')

    def create(self, validated_data):
        validated_data['quantity'] = 0
        return super().create(validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Productields = ('id', 'name', 'sku', 'quantity', 'purchase_price',
                 'sale_price', 'is_active', 'created_at')

class SupplyProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class SupplyCreateSerializer(serializers.ModelSerializer):
    products = SupplyProductSerializer(many=True, write_only=True)

    class Meta:
        model = Supply
        fields = ('supplier', 'delivery_date', 'invoice_number', 'notes', 'products')

    def validate(self, data):
        user = self.context['request'].user
        company = user.company

        if not company:
            raise serializers.ValidationError("Пользователь не привязан к компании")

        product_ids = [item['product_id'] for item in data.get('products', [])]
        products = Product.objects.filter(id__in=product_ids)

        for product in products:
            if product.storage.company != company:
                raise serializers.ValidationError(
                    f"Товар '{product.name}' не принадлежит вашей компании"
                )

        self.context['validated_products'] = products
        return data

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        validated_data['created_by'] = self.context['request'].user

        with transaction.atomic():
            supply = Supply.objects.create(**validated_data)

            for product_data in products_data:
                product = Product.objects.get(id=product_data['product_id'])

                SupplyProduct.objects.create(
                    supply=supply,
                    product=product,
                    quantity=product_data['quantity'],
                    purchase_price=product.purchase_price
                )

                product.quantity += product_data['quantity']
                product.save()

        return supply

class SupplyListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_cost = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Supply
        fields = ('id', 'supplier', 'supplier_name', 'delivery_date',
                 'invoice_number', 'created_by', 'created_by_name',
                 'total_cost', 'product_count', 'created_at')

    def get_total_cost(self, obj):
        return obj.total_cost()

    def get_product_count(self, obj):
        return obj.supplyproduct_set.count()

class SupplyDetailSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    products = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Supply
        fields = ('id', 'supplier', 'supplier_name', 'delivery_date',
                 'invoice_number', 'created_by', 'created_by_name',
                 'notes', 'products', 'total_cost', 'created_at')

    def get_products(self, obj):
        supply_products = SupplyProduct.objects.filter(supply=obj)
        return [
            {
                'product_id': sp.product.id,
                'product_name': sp.product.name,
                'product_sku': sp.product.sku,
                'quantity': sp.quantity,
                'purchase_price': sp.purchase_price,
                'total_cost': sp.total_cost()
            }
            for sp in supply_products
        ]

    def get_total_cost(self, obj):
        return obj.total_cost()

class AddEmployeeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            self.context['user_to_add'] = user
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким email не найден")
        return value


class ProductSaleCreateSerializer(serializers.Serializer):
    """Сериализатор для товаров в продаже при создании"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class SaleCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания продажи"""
    product_sales = ProductSaleCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Sale
        fields = ('buyer_name', 'sale_date', 'discount', 'product_sales')
        extra_kwargs = {
            'sale_date': {'required': False}
        }

    def validate(self, data):
        user = self.context['request'].user
        company = user.company

        if not company:
            raise serializers.ValidationError("Пользователь не привязан к компании")

        # Проверяем наличие товаров на складе
        product_sales_data = data.get('product_sales', [])
        errors = {}

        for item in product_sales_data:
            try:
                product = Product.objects.get(
                    id=item['product_id'],
                    storage__company=company
                )

                if product.quantity < item['quantity']:
                    errors[product.name] = f"В наличии только {product.quantity} шт."

            except Product.DoesNotExist:
                errors[f"product_{item['product_id']}"] = "Товар не найден в вашей компании"

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        product_sales_data = validated_data.pop('product_sales')
        user = self.context['request'].user
        company = user.company

        with transaction.atomic():
            # Создаем продажу
            sale = Sale.objects.create(
                company=company,
                created_by=user,
                **validated_data
            )

            # Создаем записи в ProductSale и уменьшаем количество товаров
            for item in product_sales_data:
                product = Product.objects.get(id=item['product_id'])

                ProductSale.objects.create(
                    sale=sale,
                    product=product,
                    quantity=item['quantity'],
                    sale_price=product.sale_price
                )

                # Уменьшаем количество товара на складе
                product.quantity -= item['quantity']
                if product.quantity < 0:
                    product.quantity = 0
                product.save()

        return sale


class ProductSaleDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для товаров в детальной информации о продаже"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductSale
        fields = ('product', 'product_name', 'product_sku',
                  'quantity', 'sale_price', 'total_price')

    def get_total_price(self, obj):
        return obj.total_price()


class SaleListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка продаж"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ('id', 'buyer_name', 'sale_date', 'created_by', 'created_by_name',
                  'discount', 'total_amount', 'final_amount', 'profit',
                  'product_count', 'created_at')

    def get_total_amount(self, obj):
        return obj.total_amount()

    def get_final_amount(self, obj):
        return obj.final_amount()

    def get_profit(self, obj):
        return obj.profit()

    def get_product_count(self, obj):
        return obj.productsale_set.count()

class SaleDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о продаже"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ('id', 'company', 'buyer_name', 'sale_date', 'created_by',
                 'created_by_name', 'discount', 'total_amount', 'discount_amount',
                 'final_amount', 'profit', 'products', 'created_at')

    def get_total_amount(self, obj):
        return obj.total_amount()

    def get_discount_amount(self, obj):
        return obj.discount_amount()

    def get_final_amount(self, obj):
        return obj.final_amount()

    def get_profit(self, obj):
        return obj.profit()

    def get_products(self, obj):
        product_sales = ProductSale.objects.filter(sale=obj)
        serializer = ProductSaleDetailSerializer(product_sales, many=True)
        return serializer.data

class SaleUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления продажи (только buyer_name и sale_date)"""
    class Meta:
        model = Sale
        fields = ('buyer_name', 'sale_date')

    def validate(self, data):
        # Запрещаем изменение количества товаров
        if 'product_sales' in self.initial_data:
            raise serializers.ValidationError(
                "Изменение количества товаров запрещено. "
                "Для изменения количества товаров отмените продажу и создайте новую."
            )
        return data

class SaleFilterSerializer(serializers.Serializer):
    """Сериализатор для фильтрации продаж по дате"""
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)