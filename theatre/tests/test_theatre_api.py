from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import (
    APIClient,
    APITestCase
)

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket
)


def _create_user(email: str, password: str, is_staff: bool = False):
    """Create a user for tests."""
    return get_user_model().objects.create_user(
        email=email,
        password=password,
        is_staff=is_staff,
    )


def _get_access_token(client: APIClient, email: str, password: str) -> str:
    """Get JWT access token using SimpleJWT endpoint."""
    url = reverse("users:token_obtain_pair")
    res = client.post(
        url,
        {
            "email": email,
            "password": password
        }, format="json")
    assert res.status_code == status.HTTP_200_OK
    return res.data["access"]


class TestTheatreApi(APITestCase):
    """Main integration-ish tests for theatre endpoints."""

    def setUp(self):
        """Create base objects and API client."""
        self.client = APIClient()

        self.user_password = "testpass123"
        self.user = _create_user(
            "user@example.com",
            self.user_password
        )
        self.admin = _create_user(
            "admin@example.com",
            self.user_password,
            is_staff=True
        )

        self.actor = Actor.objects.create(
            first_name="Tom",
            last_name="Hardy"
        )
        self.genre = Genre.objects.create(name="Drama")
        self.play = Play.objects.create(
            title="My Play",
            description="Just a test play"
        )
        self.play.actors.add(self.actor)
        self.play.genres.add(self.genre)

        self.hall = TheatreHall.objects.create(
            name="Main Hall",
            rows=5,
            seats_in_row=10
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now() + timedelta(days=1),
        )

    def test_auth_is_required_for_safe_methods(self):
        """Unauthenticated user should not be able to see lists."""
        url = reverse("theatre:actor-list")
        res = self.client.get(url)
        self.assertIn(
            res.status_code, (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN
            ))

    def test_authenticated_user_can_list_actors(self):
        """Authenticated user can read actors list."""
        token = _get_access_token(
            self.client,
            self.user.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:actor-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["results"]), 1)

    def test_non_staff_cannot_create_actor(self):
        """Non-admin user should not be able to create Actor."""
        token = _get_access_token(
            self.client,
            self.user.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:actor-list")
        payload = {"first_name": "Keanu", "last_name": "Reeves"}
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_actor(self):
        """Admin user can create Actor."""
        token = _get_access_token(
            self.client,
            self.admin.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:actor-list")
        payload = {
            "first_name": "Keanu",
            "last_name": "Reeves"
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Actor.objects.filter(
            first_name="Keanu",
            last_name="Reeves"
        ).exists())

    def test_filter_plays_by_actor_and_genre(self):
        """Plays endpoint supports filtering by actors and genres query params."""
        token = _get_access_token(self.client, self.user.email, self.user_password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:play-list")
        res = self.client.get(
            url,
            {
                "actors": str(self.actor.id),
                "genres": str(self.genre.id)
            })

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in res.data["results"]]
        self.assertIn(self.play.title, titles)

    def test_user_can_create_reservation_with_tickets(self):
        """Admin can create reservation and tickets in one request."""
        token = _get_access_token(
            self.client,
            self.admin.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:reservation-list")
        payload = {
            "performance": self.performance.id,
            "tickets": [
                {"row": 1, "seat": 1},
                {"row": 1, "seat": 2},
            ],
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Reservation.objects.filter(user=self.admin).exists())
        self.assertEqual(Ticket.objects.filter(
            reservation__user=self.admin
        ).count(), 2)

    def test_reservation_rejects_taken_seat(self):
        """If a seat is already taken for performance, API should return 400."""
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            reservation=reservation,
            performance=self.performance,
            row=2,
            seat=3,
        )

        token = _get_access_token(
            self.client,
            self.admin.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:reservation-list")
        payload = {
            "performance": self.performance.id,
            "tickets": [{"row": 2, "seat": 3}],
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tickets", res.data)

    def test_ticket_list_is_only_for_current_user(self):
        """Tickets endpoint should show only tickets for the authenticated user."""
        reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            reservation=reservation,
            performance=self.performance,
            row=3,
            seat=1,
        )
        other = _create_user("other2@example.com", self.user_password)
        other_reservation = Reservation.objects.create(user=other)
        Ticket.objects.create(
            reservation=other_reservation,
            performance=self.performance,
            row=3,
            seat=2,
        )

        token = _get_access_token(
            self.client,
            self.user.email,
            self.user_password
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("theatre:ticket-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.data.get("results", res.data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["row"], 3)
        self.assertEqual(items[0]["seat"], 1)
