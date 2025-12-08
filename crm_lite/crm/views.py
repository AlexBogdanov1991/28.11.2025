from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from .models import User, Company, Storage, Supplier, Product, Supply, Sale
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
            # Делаем пользователя владельцем компании
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
        # Привязываем склад к компании пользователя
        serializer.save(company=self.request.user.company)


class StorageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StorageSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def get_queryset(self):
        return Storage.objects.filter(company=self.request.user.company)


class SupplierListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        return Supplier.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        return Supplier.objects.filter(company=self.request.user.company)


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        if hasattr(self.request.user, 'company') and self.request.user.company:
            return Product.objects.filter(storage__company=self.request.user.company)
        return Product.objects.none()

    def perform_create(self, serializer):
        # Автоматически привязываем к складу компании
        storage = Storage.objects.get(company=self.request.user.company)
        serializer.save(storage=storage)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializerpermission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        if hasattr(self.request.user, 'company') and self.request.user.company:
            return Product.objects.filter(storage__company=self.request.user.company)
        return Product.objects.none()

class SupplyListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        return Supply.objects.filter(supplier__company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class SupplyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyEmployee]

    def get_queryset(self):
        return Supply.objects.filter(supplier__company=self.request.user.company)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyOwner])
def add_employee(request):
    """
    Добавление сотрудника в компанию
    """
    email = request.data.get('email')

    if not email:
        return Response({"error": "Email обязателен"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_to_add = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

    if user_to_add.is_company_owner:
        return Response({"error": "Владелец компании не может быть добавлен как сотрудник"},
                       status=status.HTTP_400_BAD_REQUEST)

    if user_to_add.company:
        return Response({"error": "Пользователь уже привязан к другой компании"},
                       status=status.HTTP_400_BAD_REQUEST)

    # Добавляем пользователя в компанию
    user_to_add.company = request.user.company
    user_to_add.save()

    return Response({"message": "Сотрудник успешно добавлен"}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyOwner])
def company_employees(request):
    """
    Получение списка сотрудников компании
    """
    employees = User.objects.filter(company=request.user.company, is_company_owner=False)
    serializer = UserSerializer(employees, many=True)
    return Response(serializer.data)