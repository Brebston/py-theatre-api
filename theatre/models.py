from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Actor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    class Meta:
        ordering = ("last_name", "first_name")

    def __str__(self) -> str:
        return self.first_name + " " + self.last_name


class Genre(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Play(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    actors = models.ManyToManyField(Actor, related_name="plays", blank=True)
    genres = models.ManyToManyField(Genre, related_name="plays", blank=True)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


class TheatreHall(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Performance(models.Model):
    play = models.ForeignKey(Play, on_delete=models.CASCADE, related_name="performances")
    theatre_hall = models.ForeignKey(
        TheatreHall,
        on_delete=models.PROTECT,
        related_name="performances"
    )
    show_time = models.DateTimeField()

    class Meta:
        ordering = ("show_time",)
        constraints = [
            models.UniqueConstraint(
                fields=("theatre_hall", "show_time"),
                name="uniq_hall_show_time",
            )
        ]

    def __str__(self) -> str:
        return f"{self.play.title} @ {self.theatre_hall.name} ({self.show_time:%Y-%m-%d %H:%M})"


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Reservation #{self.pk} by {self.user}"


class Ticket(models.Model):
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()

    performance = models.ForeignKey(
        Performance,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("performance", "row", "seat"),
                name="uniq_ticket_place_performance",
            )
        ]

    def clean(self):
        hall = self.performance.theatre_hall if self.performance_id else None
        if hall:
            if not (1 <= self.row <= hall.rows):
                raise ValidationError({"row": f"Row must be in range 1..{hall.rows}."})
            if not (1 <= self.seat <= hall.seats_in_row):
                raise ValidationError(
                    {"seat": f"Seat must be in range 1..{hall.seats_in_row}."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Ticket #{self.pk}: r{self.row}s{self.seat} ({self.performance})"
