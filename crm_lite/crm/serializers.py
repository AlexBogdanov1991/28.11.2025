from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User, Company, Storage, Supplier, Product, Supply, Sale


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
    class Meta:
        model = Supplier
        fields = ('id', 'company', 'name', 'inn', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_inn(self, value):
        if not value.isdigit() or len(value) not in [10, 12]:
            raise serializers.ValidationError("ИНН должен содержать 10 или 12 цифр")
        return value


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'storage', 'name', 'description', 'quantity',
                  'purchase_price', 'sale_price', 'created_at')
        read_only_fields = ('id', 'created_at', 'quantity')


class SupplyProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class SupplySerializer(serializers.ModelSerializer):
    products = SupplyProductSerializer(many=True, write_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Supply
        fields = ('id', 'supplier', 'supplier_name', 'delivery_date','created_by', 'created_by_name', 'products', 'created_at')
        read_only_fields = ('id', 'created_at', 'created_by')

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        supply = Supply.objects.create(**validated_data)

        # Обновляем количество товаров
        for product_data in products_data:
            product = Product.objects.get(id=product_data['product_id'])
            product.quantity += product_data['quantity']
            product.save()

        return supply

class SaleProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class SaleSerializer(serializers.ModelSerializer):
    products = SaleProductSerializer(many=True, write_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        fields = ('id', 'company', 'buyer_name', 'created_by', 'created_by_name',
                 'discount', 'products', 'total_amount', 'created_at')
        read_only_fields = ('id', 'created_at', 'created_by', 'total_amount')