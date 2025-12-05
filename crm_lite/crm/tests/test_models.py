from django.test import TestCase
from django.contrib.auth import get_user_model
from crm.models import Company, Storage

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.get_full_name(), 'John Doe')
        self.assertFalse(user.is_company_owner)


class CompanyModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )

    def test_company_creation(self):
        self.assertEqual(self.company.inn, '1234567890')
        self.assertEqual(self.company.name, 'Test Company')
        self.assertIsNotNone(self.company.created_at)


class StorageModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            inn='1234567890',
            name='Test Company'
        )
        self.storage = Storage.objects.create(
            company=self.company,
            address='Test Address'
        )

    def test_storage_creation(self):
        self.assertEqual(self.storage.company, self.company)
        self.assertEqual(self.storage.address, 'Test Address')