from django.db import transaction

from rest_framework import serializers

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket
)


class ActorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class GenreSerializer(serializers.ModelSerializer):

    class Meta:
        model = Genre
        fields = ("id", "name")


class PlaySerializer(serializers.ModelSerializer):
    actors = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name"
    )
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name"
    )

    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "description",
            "actors",
            "genres"
        )


class TheatreHallSerializer(serializers.ModelSerializer):

    class Meta:
        model = TheatreHall
        fields = ("id", "name", "rows", "seats_in_row")


class PerformanceSerializer(serializers.ModelSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    theatre_hall_name = serializers.CharField(source="theatre_hall.name", read_only=True)

    class Meta:
        model = Performance
        fields = ("id", "play_title", "theatre_hall_name", "show_time")


class TicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = ("id", "play", "theatre_hall", "show_time")


class TicketCreateItemSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=1)
    seat = serializers.IntegerField(min_value=1)


class ReservationListSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "tickets")


class ReservationCreateSerializer(serializers.ModelSerializer):
    performance = serializers.PrimaryKeyRelatedField(
        queryset=Performance.objects.all(),
        write_only=True
    )
    tickets = TicketCreateItemSerializer(many=True, write_only=True)

    class Meta:
        model = Reservation
        fields = ("id", "created_at", "performance", "tickets")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        performance = attrs["performance"]
        hall = performance.theatre_hall
        tickets = attrs["tickets"]

        if not tickets:
            raise serializers.ValidationError(
                {"tickets": "Provide at least one ticket."}
            )

        seen = set()
        for ticket in tickets:
            row, seat = ticket["row"], ticket["seat"]

            if row < 1 or row > hall.rows:
                raise serializers.ValidationError(
                    {"tickets": f"Row {row} is out of range 1..{hall.rows}."}
                )
            if seat < 1 or seat > hall.seats_in_row:
                raise serializers.ValidationError(
                    {"tickets": f"Seat {seat} is out of range 1..{hall.seats_in_row}."}
                )

            key = (row, seat)
            if key in seen:
                raise serializers.ValidationError(
                    {"tickets": f"Duplicate seat in request: row {row}, seat {seat}."}
                )
            seen.add(key)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        performance = validated_data.pop("performance")
        tickets_data = validated_data.pop("tickets")

        request = self.context["request"]
        reservation = Reservation.objects.create(user=request.user)

        tickets = [
            Ticket(
                reservation=reservation,
                performance=performance,
                row=item["row"],
                seat=item["seat"],
            )
            for item in tickets_data
        ]

        try:
            Ticket.objects.bulk_create(tickets)
        except Exception:
            raise serializers.ValidationError(
                {"tickets": "One or more seats are already taken for this performance."}
            )

        return reservation