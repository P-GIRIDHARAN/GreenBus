from django.http import Http404
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from tutorial.quickstart.views import UserViewSet

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel
from GreenBus_App.serializers import BusSerializer, UserSerializer, TicketSerializer, PaymentSerializer, \
    CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset =CompanyModel.objects.all()
    serializer_class = CompanySerializer

class BusViewSet(viewsets.ModelViewSet):
    queryset =BusModel.objects.all()
    serializer_class = BusSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset =UserModel.objects.all()
    serializer_class = UserSerializer

class TicketViewSet(viewsets.ModelViewSet):
    queryset =TicketModel.objects.all()
    serializer_class = TicketSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset =PaymentModel.objects.all()
    serializer_class = PaymentSerializer
@api_view(["GET"])
def SearchBuses(request):
    from_location=request.GET.get("fromWhere")
    to_location=request.GET.get("toWhere")
    time = request.GET.get("date")
    buses=BusModel.objects.filter(fromWhere=from_location,toWhere=to_location,date=time)
    serializer=BusSerializer(buses,many=True)
    return Response(serializer.data)
@api_view(["GET"])
def BusCompanyList(request, company_id):
    try:
        company = CompanyModel.objects.get(id=company_id)
    except CompanyModel.DoesNotExist:
        raise Http404("Company not found")
    buses = BusModel.objects.filter(busCompany=company).values("busNo", "fromWhere", "toWhere", "boardingTime", "date")

    return Response({
        "company": company.busCompany,
        "noOfBuses": company.noOfBuses,
        "buses": list(buses)
    })

