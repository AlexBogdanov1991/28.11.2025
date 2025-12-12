from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import User, Company, Storage, Supplier, Product, Supply, SupplyProduct
from .serializers import *
from .permissions import IsCompanyOwner, IsCompanyEmployee


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