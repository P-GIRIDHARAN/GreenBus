from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CASCADE
from django.urls import reverse
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError


class UserModel(models.Model):
    customerId=models.CharField(max_length=20,unique=True)
    firstName=models.CharField(max_length=20)
    lastName=models.CharField(max_length=20)
    age=models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15)
    def __str__(self):
        return f"{self.firstName} {self.lastName}"

class CompanyModel(models.Model):
    busCompany=models.CharField(max_length=20)
    noOfBuses = models.PositiveIntegerField(default=0, editable=False)
    def __str__(self):
        return f"{self.busCompany}"

class BusModel(models.Model):
    busNo = models.PositiveIntegerField(unique=True, default=1)
    busCompany = models.ForeignKey("CompanyModel", on_delete=CASCADE)
    totalSeats = models.PositiveIntegerField(default=40)  # Total seats in bus
    availableSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)  # Available seats
    bookedSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)  # Booked seats
    fromWhere = models.CharField(max_length=20)
    toWhere = models.CharField(max_length=20)
    perSeatPrice = models.PositiveIntegerField(default=500)
    TIME_CHOICES = [("Morning", "9AM"), ("Night", "9PM")]
    boardingTime = models.CharField(choices=TIME_CHOICES)
    date = models.DateField(default=now)

    def __str__(self):
        return f"{self.busNo} - {self.busCompany}"

    def save(self, *args, **kwargs):
        """Initialize available seats when a new bus is created."""
        if not self.availableSeats:
            self.availableSeats = list(range(1, self.totalSeats + 1))
        super().save(*args, **kwargs)

    def update_seat_status(self):
        """Update available and booked seats based on `RouteModel`."""
        booked_seats = set()
        for route in self.routes.all():
            booked_seats.update(route.bookedSeats)

        self.bookedSeats = list(booked_seats)
        self.availableSeats = [seat for seat in range(1, self.totalSeats + 1) if seat not in booked_seats]
        self.save()


class RouteModel(models.Model):
    bus = models.ForeignKey(BusModel, on_delete=CASCADE, related_name="routes")
    stopName = models.CharField(max_length=50)
    stopOrder = models.PositiveIntegerField()
    bookedSeats = ArrayField(models.PositiveIntegerField(), blank=True, default=list)  # Tracks booked seats

    class Meta:
        ordering = ["stopOrder"]

    def __str__(self):
        return f"{self.bus.busNo} - {self.stopName}"

    def is_seat_available(self, seat_number):
        return seat_number not in self.bookedSeats

    def book_seat(self, seat_number):
        """Book a seat and update `BusModel`."""
        if not self.is_seat_available(seat_number):
            raise ValueError(f"Seat {seat_number} is already booked at {self.stopName}.")
        self.bookedSeats.append(seat_number)
        self.save()
        self.bus.update_seat_status()

    def release_seat(self, seat_number):
        """Release a booked seat and update `BusModel`."""
        if seat_number in self.bookedSeats:
            self.bookedSeats.remove(seat_number)
            self.save()
            self.bus.update_seat_status()

class TicketModel(models.Model):
    ticketId=models.IntegerField(unique=True)
    customerName=models.ForeignKey("UserModel",on_delete=CASCADE)
    busNo=models.ForeignKey("BusModel",on_delete=CASCADE)
    seatSelected=ArrayField(models.CharField(max_length=200), blank=True,default=list)
    ticket_price=models.PositiveIntegerField(default=0,editable=False)
    def __str__(self):
        return f"Ticket Id-{self.ticketId} for {self.busNo} Booked By {self.customerName.firstName}"

    def validate(self):
        bus=self.busNo
        if self.seatSelected ==[]:
                raise(ValidationError("Please select any seat"))
        if not set(self.seatSelected).issubset(set(bus.availableSeats)):
            raise(ValidationError("One or more seats selected not available in Bus"))
    def save(self, *args, **kwargs):
        self.validate()
        bus = self.busNo
        if self.seatSelected and isinstance(bus.availableSeats, list):
            updated_seats = [seat for seat in bus.availableSeats if
                             seat not in self.seatSelected]  # Remove selected seats
            bus.availableSeats=updated_seats
            bus.save()
        seat_count = len(self.seatSelected)
        self.ticket_price = seat_count * self.busNo.perSeatPrice
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.seatSelected:
            bus = self.busNo
            bus.availableSeats.extend(self.seatSelected)  # Add seats back
            bus.availableSeats = list(set(bus.availableSeats))  # Remove duplicates if any
            bus.save()
        super().delete(*args, **kwargs)

class PaymentModel(models.Model):
    PAYMENT_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled")
    ]
    customerName=models.ForeignKey("UserModel",on_delete=CASCADE)
    ticketId=models.ForeignKey("TicketModel",on_delete=CASCADE)
    paymentStatus=models.CharField(max_length=10,choices=PAYMENT_CHOICES,default="Pending")
