from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class StudentProfileAPITestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='student@test.com',
            password='testpassword123',
            first_name='Test',
            last_name='Student',
            college='Test College',
            graduation_year=2027,
        )

        self.url = '/api/profile/'

    def test_unauthenticated_user_cannot_access_profile(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_authenticated_user_can_get_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data['phone'],
            ''
        )

    def test_authenticated_user_can_update_profile(self):
        self.client.force_authenticate(user=self.user)

        data = {
            'phone': '9876543210',
            'branch': 'Computer Science and Engineering',
            'cgpa': '8.70',
            'skills': 'Python, Java, SQL',
            'bio': 'Computer Science student',
        }

        response = self.client.patch(
            self.url,
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data['cgpa'],
            '8.70'
        )

        self.assertEqual(
            response.data['branch'],
            'Computer Science and Engineering'
        )