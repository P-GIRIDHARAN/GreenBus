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

    def save(self, *args, **kwargs):
        """Initialize available seats when a new bus is created."""
        if not self.availableSeats:
            self.availableSeats = list(range(1, self.totalSeats + 1))
        super().save(*args, **kwargs)

    def update_seat_status(self):
        """Dynamically update available and booked seats per segment."""
        all_seats = set(range(1, self.totalSeats + 1))  # Full seat list
        booked_seats = set()  # Store booked seats
        available_seats = all_seats.copy()  # Initially assume all are available

        # Loop through each route stop and track booked seats correctly
        for route in self.routes.all().order_by("stopOrder"):
            for seat in route.bookedSeats:
                booked_seats.add(seat)  # Add to booked list
                available_seats.discard(seat)  # Remove from available seats

        # Ensure bookedSeats and availableSeats are correctly updated
        self.bookedSeats = sorted(booked_seats)
        self.availableSeats = sorted(available_seats)

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

    def book_seat(self, seat_number, from_stop, to_stop):
        bus = self.bus
        route_stops = list(bus.routes.order_by("stopOrder"))

        from_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == from_stop), None)
        to_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == to_stop), None)

        if from_index is None or to_index is None or from_index >= to_index:
            raise ValueError("Invalid stop selection.")

        for stop in route_stops[from_index:to_index]:
            if seat_number in stop.bookedSeats:
                raise ValueError(f"Seat {seat_number} is already booked on this segment.")

        for stop in route_stops[from_index:to_index]:
            stop.bookedSeats.append(seat_number)
            stop.save()

        bus.update_seat_status()


class TicketModel(models.Model):
    ticketId = models.AutoField(primary_key=True)
    customer = models.ForeignKey("UserModel", on_delete=CASCADE)
    bus = models.ForeignKey("BusModel", on_delete=CASCADE)
    seatNumbers = ArrayField(models.PositiveIntegerField(), blank=True, default=list)
    fromStop = models.CharField(max_length=50)
    toStop = models.CharField(max_length=50)
    ticketPrice = models.PositiveIntegerField(default=0, editable=False)
    bookingDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.ticketId} - Bus {self.bus.busNo} - Seats {self.seatNumbers}"

    def validate_booking(self):
        route_stops = self.bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        if self.fromStop not in stop_names or self.toStop not in stop_names:
            raise ValidationError("Invalid stops selected.")

        from_index = stop_names.index(self.fromStop)
        to_index = stop_names.index(self.toStop)

        if from_index >= to_index:
            raise ValidationError("Invalid journey sequence.")

        # Check seat availability for the segment
        for stop in route_stops[from_index:to_index]:
            for seat in self.seatNumbers:
                if seat in stop.bookedSeats:
                    raise ValidationError(f"Seat {seat} is already booked on this route.")

    def save(self, *args, **kwargs):
        self.validate_booking()
        route_stops = self.bus.routes.order_by("stopOrder")
        from_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == self.fromStop)
        to_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == self.toStop)

        for stop in route_stops[from_index:to_index]:
            for seat in self.seatNumbers:
                stop.bookedSeats.append(seat)
                stop.save()

        self.ticketPrice = len(self.seatNumbers) * self.bus.perSeatPrice
        super().save(*args, **kwargs)

        # Update bus available/booked seats
        self.bus.update_seat_status()

    def delete(self, *args, **kwargs):
        """Release seats for only the booked segment."""
        route_stops = self.bus.routes.order_by("stopOrder")

        from_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == self.fromStop)
        to_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == self.toStop)

        for stop in route_stops[from_index:to_index]:
            for seat in self.seatNumbers:
                if seat in stop.bookedSeats:
                    stop.bookedSeats.remove(seat)
                    stop.save()

        super().delete(*args, **kwargs)

        # Update bus available seats after deletion
        self.bus.update_seat_status()


class PaymentModel(models.Model):
    PAYMENT_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled")
    ]
    customerName = models.ForeignKey("UserModel", on_delete=CASCADE)
    ticketId = models.ForeignKey("TicketModel", on_delete=CASCADE)
    paymentStatus = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="Pending")

    def save(self, *args, **kwargs):
        """
        When payment is cancelled, release the booked seats.
        """
        if self.paymentStatus == "Cancelled":
            self.release_booked_seats()

        super().save(*args, **kwargs)

    def release_booked_seats(self):
        """
        Releases seats when a payment is cancelled.
        """
        ticket = self.ticketId
        bus = ticket.bus
        route_stops = bus.routes.order_by("stopOrder")

        from_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == ticket.fromStop)
        to_index = next(i for i, stop in enumerate(route_stops) if stop.stopName == ticket.toStop)

        for stop in route_stops[from_index:to_index]:
            for seat in ticket.seatNumbers:
                if seat in stop.bookedSeats:
                    stop.bookedSeats.remove(seat)
                    stop.save()

        # Remove seats from bookedSeats and add them to availableSeats
        bus.bookedSeats = [seat for seat in bus.bookedSeats if seat not in ticket.seatNumbers]
        bus.availableSeats.extend(ticket.seatNumbers)
        bus.availableSeats.sort()  # Keep seats in ascending order
        bus.save(update_fields=["bookedSeats", "availableSeats"])
