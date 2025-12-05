from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/login/', views.user_login, name='login'),

    # Компании
    path('companies/', views.CompanyCreateView.as_view(), name='company-create'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company-detail'),

    # Склады
    path('storages/', views.StorageCreateView.as_view(), name='storage-create'),
    path('storages/<int:pk>/', views.StorageDetailView.as_view(), name='storage-detail'),

    # Поставщики
    path('suppliers/', views.SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),

    # Товары
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Поставки
    path('supplies/', views.SupplyListCreateView.as_view(), name='supply-list-create'),
    path('supplies/<int:pk>/', views.SupplyDetailView.as_view(), name='supply-detail'),

    # Сотрудники
    path('employees/add/', views.add_employee, name='add-employee'),
    path('employees/', views.company_employees, name='company-employees'),
]