from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import User, Company, Storage, Supplier, Product, Supply, SupplyProduct
from .serializers import *
from .permissions import IsCompanyOwner, IsCompanyEmployee
from django.db.models import Sum, F


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_login(request):
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_company_owner': user.is_company_owner,
            }
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyCreateView(generics.CreateAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        with transaction.atomic():
            company = serializer.save()
            self.request.user.company = company
            self.request.user.is_company_owner = True
            self.request.user.save()


class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def get_queryset(self):
        return Company.objects.filter(users=self.request.user)


class StorageCreateView(generics.CreateAPIView):
    serializer_class = StorageSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class StorageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StorageSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def get_queryset(self):
        return Storage.objects.filter(company=self.request.user.company)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        return Supplier.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'company') and self.request.user.company:
            return Product.objects.filter(
                storage__company=self.request.user.company,
                is_active=True
            )
        return Product.objects.none()

    def perform_create(self, serializer):
        try:
            storage = Storage.objects.get(company=self.request.user.company)
            serializer.save(storage=storage, quantity=0)
        except Storage.DoesNotExist:
            raise serializers.ValidationError("Сначала создайте склад для компании")


class SupplyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_serializer_class(self):
        if self.action == 'create':
            return SupplyCreateSerializer
        elif self.action == 'list':
            return SupplyListSerializer
        return SupplyDetailSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'company') and self.request.user.company:
            return Supply.objects.filter(supplier__company=self.request.user.company)
        return Supply.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        supply = self.get_object()

        with transaction.atomic():
            supply_products = SupplyProduct.objects.filter(supply=supply)
            for sp in supply_products:
                product = sp.product
                product.quantity -= sp.quantity
                if product.quantity < 0:
                    product.quantity = 0
                product.save()

            return super().destroy(request, *args, **kwargs)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyOwner])
def add_employee(request):
    serializer = AddEmployeeSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user_to_add = serializer.context['user_to_add']
        current_user = request.user

        if user_to_add.is_company_owner:
            return Response(
                {"error": "Владелец компании не может быть добавлен как сотрудник"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user_to_add.company:
            if user_to_add.company == current_user.company:
                return Response(
                    {"error": "Пользователь уже является сотрудником вашей компании"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {"error": "Пользователь уже привязан к другой компании"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user_to_add.company = current_user.company
        user_to_add.save()

        return Response({
            "message": "Сотрудник успешно добавлен",
            "employee": {
                "id": user_to_add.id,
                "email": user_to_add.email,
                "first_name": user_to_add.first_name,
                "last_name": user_to_add.last_name
            }
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated, IsCompanyOwner])
def remove_employee(request, user_id):
    try:
        employee = User.objects.get(id=user_id, company=request.user.company)

        if employee.is_company_owner:
            return Response(
                {"error": "Нельзя удалить владельца компании"},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee.company = None
        employee.save()

        return Response({
            "message": "Сотрудник успешно удален из компании"
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {"error": "Сотрудник не найден в вашей компании"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyEmployee])
def company_employees(request):
    employees = User.objects.filter(company=request.user.company)
    serializer = UserSerializer(employees, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyEmployee])
def products_on_stock(request):
    products = Product.objects.filter(
        storage__company=request.user.company,
        is_active=True
    ).order_by('name')

    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)


from django.utils import timezone
from datetime import datetime, timedelta
from .models import Sale, ProductSale


class SaleViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с продажами"""
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SaleUpdateSerializer
        elif self.action == 'list':
            return SaleListSerializer
        return SaleDetailSerializer

    def get_queryset(self):
        # Фильтрация по дате
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        queryset = Sale.objects.filter(company=self.request.user.company)

        if start_date:
            queryset = queryset.filter(sale_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__lte=end_date)

        return queryset.order_by('-sale_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """Удаление продажи с возвратом товаров на склад"""
        with transaction.atomic():
            # Возвращаем товары на склад
            product_sales = ProductSale.objects.filter(sale=instance)
            for ps in product_sales:
                product = ps.product
                product.quantity += ps.quantity
                product.save()

            # Удаляем продажу
            instance.delete()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyEmployee])
def sales_statistics(request):
    """
    Получение статистики по продажам за период
    """
    # Параметры фильтрации
    period = request.query_params.get('period', 'month')  # day, week, month, year, custom
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    # Определяем период
    today = timezone.now().date()

    if period == 'day':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == 'custom' and start_date and end_date:
        # Используем переданные даты
        pass
    else:
        # По умолчанию - текущий месяц
        start_date = today.replace(day=1)
        end_date = today

    # Получаем продажи за период
    sales = Sale.objects.filter(
        company=request.user.company,
        sale_date__gte=start_date,
        sale_date__lte=end_date
    )

    # Рассчитываем статистику
    total_sales = sales.count()
    total_amount = sum(sale.final_amount() for sale in sales)
    total_profit = sum(sale.profit() for sale in sales)

    # ТОП товаров по количеству продаж
    product_sales = ProductSale.objects.filter(
        sale__in=sales
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('sale_price'))
    ).order_by('-total_quantity')[:10]

    # ТОП товаров по прибыли
    profitable_products = ProductSale.objects.filter(
        sale__in=sales
    ).annotate(
        profit_per_item=F('sale_price') - F('product__purchase_price'),
        total_profit=F('profit_per_item') * F('quantity')
    ).values('product__name').annotate(
        total_profit=Sum('total_profit')
    ).order_by('-total_profit')[:10]

    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'statistics': {
            'total_sales': total_sales,
            'total_amount': float(total_amount),'total_profit': float(total_profit),
            'average_sale_amount': float(total_amount / total_sales) if total_sales > 0 else 0
        },
        'top_products_by_quantity': list(product_sales),
        'top_products_by_profit': list(profitable_products)
    })