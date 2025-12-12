from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'supplies', views.SupplyViewSet, basename='supply')

urlpatterns = [
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/login/', views.user_login, name='login'),

    path('companies/', views.CompanyCreateView.as_view(), name='company-create'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company-detail'),

    path('storages/', views.StorageCreateView.as_view(), name='storage-create'),
    path('storages/<int:pk>/', views.StorageDetailView.as_view(), name='storage-detail'),

    path('', include(router.urls)),

    path('employees/add/', views.add_employee, name='add-employee'),
    path('employees/remove/<int:user_id>/', views.remove_employee, name='remove-employee'),
    path('employees/', views.company_employees, name='company-employees'),

    path('products/stock/', views.products_on_stock, name='products-stock'),
]