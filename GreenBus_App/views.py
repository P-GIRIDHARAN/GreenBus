from django.http import Http404, JsonResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.utils import json
from tutorial.quickstart.views import UserViewSet

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel, RouteModel
from GreenBus_App.serializers import BusSerializer, UserSerializer, TicketSerializer, PaymentSerializer, \
    CompanySerializer, RouteSerializer


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
class RouteViewSet(viewsets.ModelViewSet):
    queryset =RouteModel.objects.all()
    serializer_class = RouteSerializer


@api_view(["GET"])
def SearchBuses(request):
    """
    Searches for buses that pass through the requested `fromWhere` and `toWhere` stops.
    """
    from_stop = request.GET.get("fromWhere")
    to_stop = request.GET.get("toWhere")
    date = request.GET.get("date")
    bus_company = request.GET.get("busCompany")

    # Query buses that have the requested stops in their route
    buses = BusModel.objects.all()

    if from_stop:
        buses = buses.filter(routes__stopName=from_stop)

    if to_stop:
        buses = buses.filter(routes__stopName=to_stop)

    if date:
        buses = buses.filter(date=date)

    if bus_company:
        buses = buses.filter(busCompany=bus_company)

    # Ensure the bus has `from_stop` before `to_stop` in its route order
    valid_buses = []
    for bus in buses.distinct():
        route_stops = bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        if from_stop in stop_names and to_stop in stop_names:
            from_index = stop_names.index(from_stop)
            to_index = stop_names.index(to_stop)

            if from_index < to_index:
                valid_buses.append(bus)

    serializer = BusSerializer(valid_buses, many=True)
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


@api_view(["POST","GET"])
def book_seat(request):
    """
    Book a seat from Stop A to Stop B.
    """
    bus_id = request.data.get("bus_id")
    seat_number = int(request.data.get("seat_number"))
    from_stop = request.data.get("from_stop")
    to_stop = request.data.get("to_stop")

    # Get the bus and route
    bus = get_object_or_404(BusModel, id=bus_id)
    route_stops = bus.routes.order_by("stopOrder")

    # Get stop indexes
    from_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == from_stop), None)
    to_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == to_stop), None)

    if from_index is None or to_index is None or from_index >= to_index:
        return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

    # Check seat availability
    for stop in route_stops[from_index:to_index]:
        if seat_number in stop.bookedSeats:
            return Response({"error": "Seat already booked on this route."}, status=status.HTTP_400_BAD_REQUEST)

    # Book seat
    for stop in route_stops[from_index:to_index]:
        stop.book_seat(seat_number)

    return Response({"success": f"Seat {seat_number} booked from {from_stop} to {to_stop}."}, status=status.HTTP_200_OK)


@api_view(["POST"])
def release_seat(request):
    """
    Release a booked seat from Stop A to Stop B.
    """
    bus_id = request.data.get("bus_id")
    seat_number = int(request.data.get("seat_number"))
    from_stop = request.data.get("from_stop")
    to_stop = request.data.get("to_stop")

    # Get the bus and route
    bus = get_object_or_404(BusModel, id=bus_id)
    route_stops = bus.routes.order_by("stopOrder")

    # Get stop indexes
    from_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == from_stop), None)
    to_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == to_stop), None)

    if from_index is None or to_index is None or from_index >= to_index:
        return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

    # Release seat
    for stop in route_stops[from_index:to_index]:
        stop.release_seat(seat_number)

    return Response({"success": f"Seat {seat_number} released from {from_stop} to {to_stop}."},
                    status=status.HTTP_200_OK)


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
        pass
    ticket.delete()

    return Response({"message": "Ticket cancelled, seats restored successfully."}, status=200)