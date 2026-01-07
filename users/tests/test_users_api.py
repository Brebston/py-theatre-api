from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import (
    APIClient,
    APITestCase
)


def _create_user(email: str, password: str, **extra_fields):
    """Create a user in database."""
    return get_user_model().objects.create_user(
        email=email,
        password=password,
        **extra_fields
    )


class TestUsersApi(APITestCase):
    """Tests for users endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.password = "testpass123"

    def test_register_user_success(self):
        """User can register with email and password."""
        url = reverse("users:create")
        payload = {
            "email": "new@example.com",
            "password": self.password
        }

        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(get_user_model().objects.filter(
            email=payload["email"]
        ).exists())
        self.assertNotIn("password", res.data)

    def test_register_user_fails_for_short_password(self):
        """Password is validated by serializer (min_length=5)"""
        url = reverse("users:create")
        payload = {
            "email": "short@example.com",
            "password": "123"
        }

        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(get_user_model().objects.filter(
            email=payload["email"]
        ).exists())

    def test_jwt_token_obtain_pair(self):
        """User can obtain JWT pair"""
        user = _create_user("user@example.com", self.password)

        url = reverse("users:token_obtain_pair")
        res = self.client.post(url, {
            "email": user.email,
            "password": self.password
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_jwt_token_verify_and_refresh(self):
        """Access token should verify, and refresh should return a new access token."""
        user = _create_user("user2@example.com", self.password)

        obtain_url = reverse("users:token_obtain_pair")
        obtain_res = self.client.post(
            obtain_url,
            {
                "email": user.email,
                "password": self.password
            },
            format="json",
        )
        self.assertEqual(obtain_res.status_code, status.HTTP_200_OK)
        access = obtain_res.data["access"]
        refresh = obtain_res.data["refresh"]

        verify_url = reverse("users:token_verify")
        verify_res = self.client.post(
            verify_url,
            {"token": access},
            format="json"
        )
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)

        refresh_url = reverse("users:token_refresh")
        refresh_res = self.client.post(
            refresh_url,
            {"refresh": refresh},
            format="json"
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_me_endpoint_requires_auth(self):
        """/me/ should require authentication."""
        url = reverse("users:manage-user")
        res = self.client.get(url)

        self.assertIn(res.status_code, (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ))

    def test_me_endpoint_returns_user_data(self):
        """Authenticated user can read their profile."""
        user = _create_user("me@example.com", self.password)

        token_url = reverse("users:token_obtain_pair")
        token_res = self.client.post(
            token_url,
            {
                "email": user.email,
                "password": self.password
            }, format="json")
        access = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        url = reverse("users:manage-user")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], user.email)
        self.assertNotIn("password", res.data)

    def test_me_endpoint_can_update_password(self):
        """Authenticated user can update password via /me/."""
        user = _create_user("changepass@example.com", self.password)

        token_url = reverse("users:token_obtain_pair")
        token_res = self.client.post(
            token_url,
            {
                "email": user.email,
                "password": self.password
            }, format="json")
        access = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        url = reverse("users:manage-user")
        new_password = "newpass999"
        res = self.client.patch(url, {"password": new_password}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
