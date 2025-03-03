from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel, RouteModel


class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model=BusModel
        fields='__all__'

class CompanySerializer(serializers.ModelSerializer):
    noOfBuses = serializers.SerializerMethodField()

    class Meta:
        model = CompanyModel
        fields = ["id", "busCompany", "noOfBuses"]

    def get_noOfBuses(self, obj):
        return BusModel.objects.filter(busCompany=obj).count()


User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)  # Access from CustomUser

    class Meta:
        model = UserModel  # Corrected to UserModel
        fields = ["id", "username", "customerId", "age", "phone_number"]

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model=RouteModel
        fields='__all__'
class TicketSerializer(serializers.ModelSerializer):
    paymentStatus = serializers.SerializerMethodField()

    class Meta:
        model = TicketModel
        fields = '__all__'

    def get_paymentStatus(self, obj):
        # Ensure we filter by the correct ticket reference
        payment = PaymentModel.objects.filter(ticket=obj).order_by('-id').first()
        return payment.paymentStatus if payment and payment.paymentStatus else "Pending"

    def validate_bookingDate(self, value):
        """Ensure bookingDate is not in the past"""
        if value < date.today():
            raise serializers.ValidationError("You cannot book tickets for past dates.")
        return value
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model=PaymentModel
        fields='__all__'