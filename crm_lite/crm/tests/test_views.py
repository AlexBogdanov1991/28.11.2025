from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from crm.models import Company

User = get_user_model()


class AuthenticationTests(APITestCase):
    def test_user_registration(self):
        data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'test@example.com')

    def test_user_login(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class CompanyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_company(self):
        data = {
            'inn': '1234567890',
            'name': 'Test Company'
        }
        response = self.client.post('/api/companies/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_company_owner)
        self.assertEqual(self.user.company.name, 'Test Company')