from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from crm.models import Company, Storage, Supplier, Product, Supply

User = get_user_model()


class SupplierTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )
        self.user.company = self.company
        self.user.is_company_owner = True
        self.user.save()

        self.client.force_authenticate(user=self.user)

    def test_create_supplier(self):
        data = {
            'name': 'Test Supplier',
            'inn': '0987654321',
            'contact_person': 'Иванов Иван',
            'phone': '+79991234567',
            'email': 'supplier@example.com'
        }
        response = self.client.post('/api/suppliers/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Supplier')

        supplier = Supplier.objects.get(id=response.data['id'])
        self.assertEqual(supplier.company, self.company)

    def test_list_suppliers(self):
        Supplier.objects.create(
            company=self.company,
            name='Supplier 1',
            inn='1111111111'
        )
        Supplier.objects.create(
            company=self.company,
            name='Supplier 2',
            inn='2222222222'
        )

        response = self.client.get('/api/suppliers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ProductTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )
        self.user.company = self.company
        self.user.is_company_owner = True
        self.user.save()

        self.storage = Storage.objects.create(
            company=self.company,
            address='Test Address'
        )

        self.client.force_authenticate(user=self.user)

    def test_create_product(self):
        data = {
            'name': 'Test Product',
            'description': 'Test Description',
            'sku': 'TEST001',
            'purchase_price': '1000.00',
            'sale_price': '1500.00'
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(id=response.data['id'])
        self.assertEqual(product.quantity, 0)
        self.assertEqual(product.storage, self.storage)

    def test_list_products(self):
        Product.objects.create(
            storage=self.storage,
            name='Product 1',
            sku='P001',
            purchase_price=1000,
            sale_price=1500
        )
        Product.objects.create(
            storage=self.storage,
            name='Product 2',
            sku='P002',
            purchase_price=2000,
            sale_price=2500
        )

        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class SupplyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )
        self.user.company = self.company
        self.user.is_company_owner = True
        self.user.save()

        self.storage = Storage.objects.create(
            company=self.company,
            address='Test Address'
        )

        self.supplier = Supplier.objects.create(
            company=self.company,
            name='Test Supplier',
            inn='0987654321'
        )

        self.product1 = Product.objects.create(
            storage=self.storage,
            name='Product 1',
            sku='P001',
            purchase_price=1000,
            sale_price=1500
        )
        self.product2 = Product.objects.create(
            storage=self.storage,
            name='Product 2',
            sku='P002',
            purchase_price=2000,
            sale_price=2500
        )

        self.client.force_authenticate(user=self.user)

    def test_create_supply(self):
        data = {
            'supplier': self.supplier.id,
            'delivery_date': '2024-01-15',
            'invoice_number': 'INV-001',
            'notes': 'Test notes',
            'products': [
                {'product_id': self.product1.id, 'quantity': 10},
                {'product_id': self.product2.id, 'quantity': 5}
            ]
        }

        response = self.client.post('/api/supplies/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        supply = Supply.objects.get(id=response.data['id'])
        self.assertEqual(supply.supplier, self.supplier)

        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.quantity, 10)
        self.assertEqual(self.product2.quantity, 5)

        supply_products = supply.supplyproduct_set.all()
        self.assertEqual(supply_products.count(), 2)

class EmployeeTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )
        self.owner.company = self.company
        self.owner.is_company_owner = True
        self.owner.save()

        self.user_to_add = User.objects.create_user(
            email='employee@example.com',
            password='testpass123',
            first_name='Employee',
            last_name='User'
        )

        self.client.force_authenticate(user=self.owner)

    def test_add_employee(self):
        data = {'email': 'employee@example.com'}
        response = self.client.post('/api/employees/add/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Сотрудник успешно добавлен')

        self.user_to_add.refresh_from_db()
        self.assertEqual(self.user_to_add.company, self.company)
        self.assertFalse(self.user_to_add.is_company_owner)