from rest_framework import serializers

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel, RouteModel


class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model=BusModel
        fields='__all__'

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model=CompanyModel
        fields='__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=UserModel
        fields='__all__'
class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model=RouteModel
        fields='__all__'
class TicketSerializer(serializers.ModelSerializer):
    paymentStatus = serializers.SerializerMethodField()
    class Meta:
        model=TicketModel
        fields='__all__'

    def get_paymentStatus(self, obj):
        payment = PaymentModel.objects.filter(ticketId=obj).order_by('-id').first()
        return payment.paymentStatus if payment else "Pending"

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model=PaymentModel
        fields='__all__'