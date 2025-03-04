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
    class Meta:
        db_table='Bus Company'
        ordering=["id"]
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

    def get_booked_seats(self):
        if not self.pk:
            return []  # If bus is not saved, return empty list to avoid querying with unsaved instance
        booked_tickets = TicketModel.objects.filter(bus=self)
        booked_seats = []
        for ticket in booked_tickets:
            booked_seats.extend(ticket.seatNumbers)
        return booked_seats

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if the instance is new
        super().save(*args, **kwargs)  # Save first to ensure it has a valid primary key
        if not is_new:  # Only update seats if it's an existing instance
            self.update_seat_status(save_instance=False)  # Avoid infinite recursion

    def update_seat_status(self, save_instance=True):
        """Update availableSeats and bookedSeats dynamically based on active tickets."""
        booked_seats = set(self.get_booked_seats())  # Get seats from active tickets
        all_seats = set(range(1, self.totalSeats + 1))

        new_available_seats = sorted(all_seats - booked_seats - set(self.blockedSeats))

        if self.bookedSeats != booked_seats:
            self.bookedSeats = sorted(booked_seats)  # Ensure booked seats are updated

        if self.availableSeats != new_available_seats:
            self.availableSeats = new_available_seats

        if save_instance:
            self.save(update_fields=["availableSeats", "bookedSeats"])  # Save only updated fields

    def release_seats(self, seat_numbers):
        """Remove cancelled seats from bookedSeats and update availableSeats."""
        booked_seats = set(self.get_booked_seats())  # Get dynamically booked seats
        all_seats = set(range(1, self.totalSeats + 1))

        # Remove the cancelled seats
        booked_seats -= set(seat_numbers)

        # Recalculate available seats
        new_available_seats = sorted(all_seats - booked_seats - set(self.blockedSeats))

        self.bookedSeats = list(booked_seats)
        self.availableSeats = new_available_seats
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
    class Meta:
        db_table='Bus Routes'
        ordering=["bus"]

class TicketModel(models.Model):
    ticketId = models.AutoField(primary_key=True)
    customer = models.ForeignKey(UserModel, on_delete=CASCADE)
    bus = models.ForeignKey(BusModel, on_delete=CASCADE)
    seatNumbers = ArrayField(models.IntegerField(), default=list)
    fromStop = models.CharField(max_length=50)
    toStop = models.CharField(max_length=50)
    ticketPrice = models.PositiveIntegerField(default=0, editable=False)
    bookingDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.ticketId} - Bus {self.bus.busNo} - Seats {self.seatNumbers}"

    def save(self, *args, **kwargs):
        self.ticketPrice = len(self.seatNumbers) * self.bus.perSeatPrice
        super().save(*args, **kwargs)
        self.bus.update_seat_status()  # Recalculate booked seats after saving

    def delete(self, *args, **kwargs):
        bus = self.bus  # Get reference before deletion
        super().delete(*args, **kwargs)  # Delete ticket
        bus.update_seat_status()


class PaymentModel(models.Model):
    PAYMENT_CHOICES = [("Pending", "Pending"), ("Paid", "Paid"), ("Cancelled", "Cancelled")]
    customer = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    ticket = models.ForeignKey(TicketModel, on_delete=models.CASCADE)
    paymentStatus = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="Pending")

    def delete(self, *args, **kwargs):
        if self.paymentStatus == "Cancelled":
            self.ticket.delete()
        super().delete(*args, **kwargs)



