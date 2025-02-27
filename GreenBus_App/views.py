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

    from_stop = request.GET.get("fromWhere")
    to_stop = request.GET.get("toWhere")
    date = request.GET.get("date")
    bus_company = request.GET.get("busCompany")

    buses = BusModel.objects.all()
    if date:
        buses = buses.filter(date=date)
    if bus_company:
        buses = buses.filter(busCompany=bus_company)

    valid_buses = []

    for bus in buses.distinct():
        route_stops = bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        # Ensure both stops exist and are in the correct order
        if from_stop in stop_names and to_stop in stop_names:
            from_index = stop_names.index(from_stop)
            to_index = stop_names.index(to_stop)

            if from_index < to_index:
                booked_seats = set()
                all_seats = set(range(1, bus.totalSeats + 1))

                for stop in route_stops[from_index:to_index]:
                    booked_seats.update(stop.bookedSeats)
                available_seats =sorted( all_seats - booked_seats)
                bus.bookedSeats = list(booked_seats)
                bus.availableSeats = list(available_seats)

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

@api_view(["POST"])
def book_seat(request, bus_id):
    seat_number = int(request.data.get("seat_number"))
    from_stop = request.data.get("from_stop")
    to_stop = request.data.get("to_stop")

    bus = get_object_or_404(BusModel, id=bus_id)
    route_stops = bus.routes.order_by("stopOrder")

    from_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == from_stop), None)
    to_index = next((i for i, stop in enumerate(route_stops) if stop.stopName == to_stop), None)

    if from_index is None or to_index is None or from_index >= to_index:
        return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

    for stop in route_stops[from_index:to_index]:
        if seat_number in stop.bookedSeats:
            return Response({"error": f"Seat {seat_number} is already booked on this route."}, status=status.HTTP_400_BAD_REQUEST)

    for stop in route_stops[from_index:to_index]:
        stop.bookedSeats.append(seat_number)
        stop.save()

    if seat_number in bus.availableSeats:
        bus.availableSeats.remove(seat_number)

    if seat_number not in bus.bookedSeats:
        bus.bookedSeats.append(seat_number)

    bus.save()

    release_seat_at_stop(bus, seat_number, to_stop)

    return Response({"success": f"Seat {seat_number} booked from {from_stop} to {to_stop}."}, status=status.HTTP_200_OK)
@api_view(["POST"])
def cancel_ticket(request, ticket_id):
    """
    Cancels a ticket and releases booked seats back to available seats.
    """
    try:
        ticket = TicketModel.objects.get(ticketId=ticket_id)
    except TicketModel.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

    if ticket.paymentStatus == "Cancelled":
        return Response({"message": "Ticket is already cancelled"}, status=status.HTTP_400_BAD_REQUEST)

    # Get the associated bus
    bus = ticket.bus

    # Release seats
    for seat in ticket.seatNumbers:
        if seat in bus.bookedSeats:
            bus.bookedSeats.remove(seat)
            bus.availableSeats.append(seat)

    # Sort available seats in ascending order
    bus.availableSeats.sort()

    # Save the updates to the bus
    bus.save(update_fields=["bookedSeats", "availableSeats"])

    # Update ticket status
    ticket.paymentStatus = "Cancelled"
    ticket.save(update_fields=["paymentStatus"])

    return Response({"message": "Ticket cancelled successfully"}, status=status.HTTP_200_OK)

def release_seat_at_stop(bus, seat_number, stop_name):
    route_stop = bus.routes.filter(stopName=stop_name).first()
    if route_stop and seat_number in route_stop.bookedSeats:
        route_stop.bookedSeats.remove(seat_number)
        route_stop.save()
    upcoming_stops = bus.routes.filter(stopOrder__gt=route_stop.stopOrder)
    seat_still_booked = any(seat_number in stop.bookedSeats for stop in upcoming_stops)

    if not seat_still_booked:
        if seat_number not in bus.availableSeats:
            bus.availableSeats.append(seat_number)

        if seat_number in bus.bookedSeats:
            bus.bookedSeats.remove(seat_number)

    bus.save()


@api_view(["POST"])
def cancel_ticket(request, ticket_id):
    try:
        ticket = TicketModel.objects.get(ticketId=ticket_id)
        payment = PaymentModel.objects.filter(ticketId=ticket).order_by('-id').first()
        if not payment:
            return Response({"error": "No payment record found for this ticket."}, status=400)
        payment.paymentStatus = "Cancelled"
        payment.save(update_fields=["paymentStatus"])
        bus = ticket.bus
        for seat in ticket.seatNumbers:
            if seat in bus.bookedSeats:
                bus.bookedSeats.remove(seat)
                bus.availableSeats.append(seat)
        bus.availableSeats.sort()
        bus.save(update_fields=["availableSeats", "bookedSeats"])
        return Response({"message": "Ticket and payment cancelled, seats released."}, status=200)
    except TicketModel.DoesNotExist:
        return Response({"error": "Ticket not found."}, status=404)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
