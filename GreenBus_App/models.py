from django.contrib.auth.models import AbstractUser, Group, Permission, User
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile",null=True,blank=True)  # Use related_name="profile"
    is_customer = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


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
    blockedSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)
    fromWhere = models.CharField(max_length=20)
    toWhere = models.CharField(max_length=20)
    perSeatPrice = models.PositiveIntegerField(default=500)
    TIME_CHOICES = [("Morning", "9AM"), ("Night", "9PM")]
    boardingTime = models.CharField(choices=TIME_CHOICES, max_length=10)
    date = models.DateField(default=now)

    def save(self, *args, **kwargs):
        all_seats = set(range(1, self.totalSeats + 1))

        # Ensure bookedSeats and blockedSeats are not None before converting to sets
        booked_seats = set(self.bookedSeats or [])
        blocked_seats = set(self.blockedSeats or [])

        # Ensure there is no invalid seat number
        invalid_seats = booked_seats | blocked_seats - all_seats
        if invalid_seats:
            raise ValidationError(f"Invalid seat numbers found: {invalid_seats}")

        self.availableSeats = sorted(all_seats - booked_seats - blocked_seats)

        super().save(*args, **kwargs)

    def update_seat_status(self):
        all_seats = set(range(1, self.totalSeats + 1))
        booked_seats = set(self.bookedSeats)  # Convert to set
        blocked_seats = set(self.blockedSeats)  # Convert to set

        available_seats = all_seats - booked_seats - blocked_seats  # Ensure correct set operations

        self.bookedSeats = sorted(booked_seats)  # Store sorted list
        self.availableSeats = sorted(available_seats)  # Store sorted list
        self.save(update_fields=["bookedSeats", "availableSeats"])


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
