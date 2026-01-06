from rest_framework import viewsets

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket
)
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PlaySerializer,
    TheatreHallSerializer,
    PerformanceSerializer,
    ReservationListSerializer,
    ReservationCreateSerializer,
    TicketSerializer
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related("actors", "genres").all()
    serializer_class = PlaySerializer


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.select_related("play", "theatre_hall").all()
    serializer_class = PerformanceSerializer


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()

    def get_queryset(self):
        return (
            Reservation.objects.filter(
                user=self.request.user
            ).prefetch_related(
                "tickets",
                "tickets__performance",
                "tickets__performance__play",
                "tickets__performance__theatre_hall"
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        return ReservationListSerializer


class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_queryset(self):
        return Ticket.objects.filter(
            reservation__user=self.request.user
        ).select_related(
            "performance",
            "reservation"
        )