from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CASCADE
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError
class CustomUser(AbstractUser):
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_groups",  # Add this to avoid conflicts
        blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_permissions",  # Add this to avoid conflicts
        blank=True
    )

    def __str__(self):
        return self.username
class UserModel(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=CASCADE, null=True, blank=True)
    customerId = models.CharField(max_length=20, unique=True)
    age = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}" if self.user else "Anonymous"


class CompanyModel(models.Model):
    busCompany = models.CharField(max_length=20)
    noOfBuses = models.PositiveIntegerField(default=0, editable=False)

    def __str__(self):
        return self.busCompany


class BusModel(models.Model):
    busNo = models.PositiveIntegerField(unique=True)
    busCompany = models.ForeignKey(CompanyModel, on_delete=CASCADE)
    totalSeats = models.PositiveIntegerField(default=40)
    availableSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)
    bookedSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)
    fromWhere = models.CharField(max_length=20)
    toWhere = models.CharField(max_length=20)
    perSeatPrice = models.PositiveIntegerField(default=500)
    TIME_CHOICES = [("Morning", "9AM"), ("Night", "9PM")]
    boardingTime = models.CharField(choices=TIME_CHOICES, max_length=10)
    date = models.DateField(default=now)

    def save(self, *args, **kwargs):
        if not self.availableSeats:
            self.availableSeats = list(range(1, self.totalSeats + 1))
        super().save(*args, **kwargs)

    def update_seat_status(self):
        all_seats = set(range(1, self.totalSeats + 1))
        booked_seats = set()
        available_seats = all_seats.copy()

        for route in self.routes.all().order_by("stopOrder"):
            for seat in route.bookedSeats:
                booked_seats.add(seat)
                available_seats.discard(seat)

        self.bookedSeats = sorted(booked_seats)
        self.availableSeats = sorted(available_seats)
        self.save()


class RouteModel(models.Model):
    bus = models.ForeignKey(BusModel, on_delete=CASCADE, related_name="routes")
    stopName = models.CharField(max_length=50)
    stopOrder = models.PositiveIntegerField()
    bookedSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)

    class Meta:
        ordering = ["stopOrder"]

    def __str__(self):
        return f"{self.bus.busNo} - {self.stopName}"


class TicketModel(models.Model):
    ticketId = models.AutoField(primary_key=True)
    customer = models.ForeignKey(UserModel, on_delete=CASCADE)
    bus = models.ForeignKey(BusModel, on_delete=CASCADE)
    seatNumbers = ArrayField(models.PositiveIntegerField(), blank=True, default=list)
    fromStop = models.CharField(max_length=50)
    toStop = models.CharField(max_length=50)
    ticketPrice = models.PositiveIntegerField(default=0, editable=False)
    bookingDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.ticketId} - Bus {self.bus.busNo} - Seats {self.seatNumbers}"

    def save(self, *args, **kwargs):
        self.ticketPrice = len(self.seatNumbers) * self.bus.perSeatPrice
        super().save(*args, **kwargs)
        self.bus.update_seat_status()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.bus.update_seat_status()


class PaymentModel(models.Model):
    PAYMENT_CHOICES = [("Pending", "Pending"), ("Paid", "Paid"), ("Cancelled", "Cancelled")]
    customer = models.ForeignKey(UserModel, on_delete=CASCADE)
    ticket = models.ForeignKey(TicketModel, on_delete=CASCADE)
    paymentStatus = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="Pending")

    def save(self, *args, **kwargs):
        if self.paymentStatus == "Cancelled":
            self.ticket.delete()
        super().save(*args, **kwargs)
