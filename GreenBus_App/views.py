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
    filters = {}
    if "fromWhere" in request.GET:
        filters["fromWhere"] = request.GET.get("fromWhere")
    if "toWhere" in request.GET:
        filters["toWhere"] = request.GET.get("toWhere")
    if "date" in request.GET:
        filters["date"] = request.GET.get("date")
    if "busCompany" in request.GET:
        filters["busCompany"]=request.GET.get("busCompany")
    buses = BusModel.objects.filter(**filters)
    serializer=BusSerializer(buses,many=True)
    return Response(serializer.data)

@api_view(["GET"])
def bus_company_list(request, company_id):
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

@api_view(["POST"])
def cancel_ticket(request, ticket_id):
    try:
        ticket = TicketModel.objects.get(ticketId=ticket_id)
    except TicketModel.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=404)
    bus = ticket.busNo
    if ticket.seatSelected:
        bus.availableSeats = list(set(bus.availableSeats) | set(ticket.seatSelected))  # Add seats back
        bus.save()
    try:
        payment = PaymentModel.objects.get(ticketId=ticket)
        payment.paymentStatus = "Cancelled"
        payment.save()
    except PaymentModel.DoesNotExist:
        pass  # No payment record, so just proceed
    ticket.delete()

    return Response({"message": "Ticket cancelled, seats restored successfully."}, status=200)