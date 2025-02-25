from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CASCADE
from django.db.models.signals import post_save
from django.dispatch import receiver
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

class BusModel(models.Model):
    busNo=models.PositiveIntegerField(unique=True,default=1)
    busCompany=models.CharField(max_length=20)
    availableSeats=ArrayField(models.CharField(max_length=200), blank=True)
    fromWhere=models.CharField(max_length=20)
    toWhere=models.CharField(max_length=20)
    TIME_CHOICES = [
        ("Morning", "9AM"),
        ("Night", "9PM"),
    ]
    boardingTime=models.CharField(choices=TIME_CHOICES)
    date=models.DateField(default=now)
    def __str__(self):
        return f"{self.busCompany}"

class TicketModel(models.Model):
    ticketId=models.IntegerField(unique=True)
    customerName=models.ForeignKey(UserModel,on_delete=CASCADE)
    busCompany=models.ForeignKey(BusModel,on_delete=CASCADE)
    seatSelected=ArrayField(models.CharField(max_length=200), blank=True,default=list)
    def __str__(self):
        return f"Ticket Id-{self.ticketId} Booked By {self.customerName.firstName}"

    def validate(self):
        bus=self.busCompany
        if self.seatSelected ==[]:
                raise(ValidationError("Please select any seat"))
        if not set(self.seatSelected).issubset(set(bus.availableSeats)):
            raise(ValidationError("One or more seats selected not available in Bus"))
    def save(self, *args, **kwargs):
        self.validate()
        bus = self.busCompany
        if self.seatSelected and isinstance(bus.availableSeats, list):
            updated_seats = [seat for seat in bus.availableSeats if
                             seat not in self.seatSelected]  # Remove selected seats
            bus.availableSeats=updated_seats
            bus.save()
        super().save(*args, **kwargs)

class PaymentModel(models.Model):
    PAYMENT_CHOICES = [
        ("Paid", "Successful"),
        ("Not Paid", "Not Successful"),
    ]
    customerName=models.ForeignKey(UserModel,on_delete=CASCADE)
    ticketId=models.ForeignKey(TicketModel,on_delete=CASCADE)
    paymentStatus=models.CharField(max_length=10,choices=PAYMENT_CHOICES,default="Not Paid")

