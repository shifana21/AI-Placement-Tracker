from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class StudentRegistrationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.valid_payload = {
            'email': 'student@example.com',
            'password': 'strongpassword123',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'college': 'University of Tech',
            'graduation_year': 2027
        }

    def test_registration_success(self):
        """Test registering a student with valid data is successful."""
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        
        # Verify response status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify password is not in the response payload
        self.assertNotIn('password', response.data)
        
        # Verify user details in response
        self.assertEqual(response.data['email'], self.valid_payload['email'])
        self.assertEqual(response.data['first_name'], self.valid_payload['first_name'])
        self.assertEqual(response.data['last_name'], self.valid_payload['last_name'])
        self.assertEqual(response.data['college'], self.valid_payload['college'])
        self.assertEqual(response.data['graduation_year'], self.valid_payload['graduation_year'])
        
        # Verify user is saved in DB and password is secure/hashed
        user = User.objects.get(email=self.valid_payload['email'])
        self.assertTrue(user.check_password(self.valid_payload['password']))
        self.assertNotEqual(user.password, self.valid_payload['password'])
        self.assertEqual(user.first_name, self.valid_payload['first_name'])
        self.assertEqual(user.last_name, self.valid_payload['last_name'])
        self.assertEqual(user.college, self.valid_payload['college'])
        self.assertEqual(user.graduation_year, self.valid_payload['graduation_year'])
        
        # Verify defaults
        self.assertEqual(user.role, 'student')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_duplicate_email(self):
        """Test registration fails when the email is already registered."""
        # Create an initial user
        User.objects.create_user(
            email=self.valid_payload['email'],
            password=self.valid_payload['password'],
            first_name='Existing',
            last_name='User'
        )
        
        # Attempt to register with the same email
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_password_length_validation(self):
        """Test registration fails if the password is less than 8 characters."""
        payload = self.valid_payload.copy()
        payload['password'] = 'short1'
        
        response = self.client.post(self.register_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_registration_excludes_restricted_fields(self):
        """Test that registering cannot set role, is_staff, or is_superuser."""
        payload = self.valid_payload.copy()
        payload['role'] = 'admin'
        payload['is_staff'] = True
        payload['is_superuser'] = True
        
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Retrieve user and assert they have standard student permissions
        user = User.objects.get(email=self.valid_payload['email'])
        self.assertEqual(user.role, 'student')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_registration_missing_required_fields(self):
        """Test registration fails when email or password is missing."""
        # Missing email
        payload = self.valid_payload.copy()
        payload.pop('email')
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        
        # Missing password
        payload = self.valid_payload.copy()
        payload.pop('password')
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

