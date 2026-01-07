from django.template.context_processors import request
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

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
    PlayImageSerializer, PlaySerializer,
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

    @staticmethod
    def _params_to_ints(query_string):
        """Converts a string of format '1,2,3' to a list of integers [1,2,3]."""
        return [int(str_id) for str_id in query_string.split(",")]

    def get_serializer_class(self):
        if self.action == "upload_image":
            return PlayImageSerializer

        return PlaySerializer

    def get_queryset(self):
        queryset = self.queryset
        actors = self.request.query_params.get("actors")
        genres = self.request.query_params.get("genres")
        if actors:
            actors = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors)
        if genres:
            genres = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres)
        if self.action in ("list", "retrieve"):
            return queryset.prefetch_related("actors", "genres")

        return queryset

    @action(
        methods=["POST"],
        detail=True,
        permission_classes=[IsAdminUser],
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "actors",
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by actor id (ex. ?actors=2,3)",
            ),
            OpenApiParameter(
                "genres",
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by genre id (ex. ?genres=2,3)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of buses"""
        return super().list(request, *args, **kwargs)


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