from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel, RouteModel
from GreenBus_App.serializers import BusSerializer, UserSerializer, TicketSerializer, PaymentSerializer, \
    CompanySerializer, RouteSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = CompanyModel.objects.all()
    serializer_class = CompanySerializer


class BusViewSet(viewsets.ModelViewSet):
    queryset = BusModel.objects.all()
    serializer_class = BusSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer


class TicketViewSet(viewsets.ModelViewSet):
    queryset = TicketModel.objects.all()
    serializer_class = TicketSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = PaymentModel.objects.all()
    serializer_class = PaymentSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = RouteModel.objects.all()
    serializer_class = RouteSerializer

User = get_user_model()

@api_view(["POST"])
def register_user(request):
    try:
        data = request.data
        data["password"] = make_password(data["password"])  # Hash the password

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User registered successfully",
                    "user": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.id, "is_customer": user.is_customer},
                        status=status.HTTP_200_OK)

    return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def search_buses(request):
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

        if from_stop in stop_names and to_stop in stop_names:
            from_index = stop_names.index(from_stop)
            to_index = stop_names.index(to_stop)
            if from_index < to_index:
                valid_buses.append(bus)

    serializer = BusSerializer(valid_buses, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    if not request.user.is_superuser:
        return Response({"error": "You do not have admin privileges"}, status=status.HTTP_403_FORBIDDEN)

    buses = BusModel.objects.all()
    routes = RouteModel.objects.all()

    return Response({
        "buses": BusSerializer(buses, many=True).data,
        "routes": RouteSerializer(routes, many=True).data
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_seat(request, bus_id):
    if not request.user.is_customer:
        return Response({"error": "Only customers can book seats."}, status=status.HTTP_403_FORBIDDEN)
    seat_number = int(request.data.get("seat_number"))
    from_stop = request.data.get("from_stop")
    to_stop = request.data.get("to_stop")

    bus = get_object_or_404(BusModel, id=bus_id)
    route_stops = bus.routes.order_by("stopOrder")
    stop_names = [stop.stopName for stop in route_stops]

    from_index = stop_names.index(from_stop) if from_stop in stop_names else None
    to_index = stop_names.index(to_stop) if to_stop in stop_names else None

    if from_index is None or to_index is None or from_index >= to_index:
        return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

    for stop in route_stops[from_index:to_index]:
        if seat_number in stop.bookedSeats:
            return Response({"error": f"Seat {seat_number} is already booked on this route."},
                            status=status.HTTP_400_BAD_REQUEST)

    ticket = TicketModel.objects.create(
        customer=request.user.usermodel,
        bus=bus,
        seatNumbers=[seat_number],
        fromStop=from_stop,
        toStop=to_stop,
        ticketPrice=bus.perSeatPrice
    )
    return Response(
        {"success": f"Seat {seat_number} booked from {from_stop} to {to_stop}.", "ticket_id": ticket.ticketId},
        status=status.HTTP_200_OK)
@api_view(["POST"])
def cancel_ticket(request, ticket_id):
    try:
        ticket = TicketModel.objects.get(ticketId=ticket_id)
        payment = PaymentModel.objects.filter(ticketId=ticket_id).order_by("-id").first()

        if not payment:
            return Response({"error": "No payment record found for this ticket."}, status=status.HTTP_400_BAD_REQUEST)

        if payment.paymentStatus == "Cancelled":
            return Response({"message": "Ticket is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        payment.paymentStatus = "Cancelled"
        payment.save(update_fields=["paymentStatus"])

        ticket.delete()
        return Response({"message": "Ticket cancelled successfully."}, status=status.HTTP_200_OK)

    except TicketModel.DoesNotExist:
        return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
def get_bus_routes(request):
    routes = RouteModel.objects.all()
    serializer = RouteSerializer(routes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
