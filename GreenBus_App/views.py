from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import viewsets, status
from rest_framework.authtoken.admin import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from GreenBus_App.models import BusModel, UserModel, TicketModel, PaymentModel, CompanyModel, RouteModel
from GreenBus_App.serializers import BusSerializer, UserSerializer, TicketSerializer, PaymentSerializer, \
    CompanySerializer, RouteSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = CompanyModel.objects.all()
    serializer_class = CompanySerializer
    permission_classes=[IsAdminUser]

class BusViewSet(viewsets.ModelViewSet):
    queryset = BusModel.objects.all()
    serializer_class = BusSerializer
    permission_classes=[IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes=[IsAdminUser]


class TicketViewSet(viewsets.ModelViewSet):
    queryset = TicketModel.objects.all()
    serializer_class = TicketSerializer
    permission_classes=[IsAdminUser]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = PaymentModel.objects.all()
    serializer_class = PaymentSerializer
    permission_classes=[IsAdminUser]


class RouteViewSet(viewsets.ModelViewSet):
    queryset = RouteModel.objects.all()
    serializer_class = RouteSerializer
    permission_classes=[IsAdminUser]

@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    try:
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if get_user_model().objects.filter(username=username).exists():
            return Response({"error": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_model().objects.create(username=username, password=make_password(password))

        # Create UserModel profile
        UserModel.objects.create(user=user, is_customer=True)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response(
            {"message": "User registered successfully", "access_token": access_token},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)

    if user:
        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response(
            {
                "message": "Login successful",
                "access_token": access_token,
                "user_id": user.id
            },
            status=status.HTTP_200_OK
        )

    return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    if not request.user.is_superuser:
        return Response({"error": "You do not have admin privileges"}, status=status.HTTP_403_FORBIDDEN)

    # Your business logic
    return Response({"message": "Welcome to the admin dashboard"})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_seat(request, bus_id):
    try:
        user = request.user
        user_model = getattr(user, "profile", None)

        if not user_model:
            return Response({"error": "Only registered customers can book seats."}, status=status.HTTP_403_FORBIDDEN)

        seat_numbers = request.data.get("seat_numbers", [])
        from_stop = request.data.get("from_stop")
        to_stop = request.data.get("to_stop")

        bus = get_object_or_404(BusModel, id=bus_id)
        route_stops = bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        if from_stop not in stop_names or to_stop not in stop_names:
            return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

        from_index = stop_names.index(from_stop)
        to_index = stop_names.index(to_stop)

        if from_index >= to_index:
            return Response({"error": "Invalid journey selection."}, status=status.HTTP_400_BAD_REQUEST)

        booked_seats = set()
        for stop in route_stops[from_index:to_index]:
            booked_seats.update(stop.bookedSeats)

        blocked_seats = set(bus.blockedSeats)

        if any(seat in booked_seats for seat in seat_numbers):
            return Response({"error": "Some seats are already booked."}, status=status.HTTP_400_BAD_REQUEST)

        if any(seat in blocked_seats for seat in seat_numbers):
            return Response({"error": "Some seats are blocked and cannot be booked."}, status=status.HTTP_400_BAD_REQUEST)

        ticket = TicketModel.objects.create(
            customer=user_model,
            bus=bus,
            seatNumbers=seat_numbers,
            fromStop=from_stop,
            toStop=to_stop,
        )

        for stop in route_stops[from_index:to_index]:
            stop.bookedSeats.extend(seat_numbers)
            stop.save()

        bus.update_seat_status()

        return Response(
            {"message": "Seat(s) booked successfully.", "ticket_id": ticket.ticketId},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
@permission_classes([AllowAny])
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

                blocked_seats = set(bus.blockedSeats)
                available_seats = sorted(all_seats - booked_seats - blocked_seats)

                bus.bookedSeats = list(booked_seats)
                bus.availableSeats = list(available_seats)

                valid_buses.append(bus)

    serializer = BusSerializer(valid_buses, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def get_bus_routes(request):
    bus_id = request.data.get("bus_id")
    if not bus_id:
        return Response({"error": "Bus ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Fetch the routes related to the given bus and order them by stop order
    routes = RouteModel.objects.filter(bus_id=bus_id).order_by("stopOrder")

    # Serialize the routes
    serializer = RouteSerializer(routes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def make_payment(request):
    try:
        ticket_id = request.data.get("ticket_id")

        if not ticket_id:
            return Response({"error": "Ticket ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        ticket = get_object_or_404(TicketModel, ticketId=ticket_id)

        # Check if a payment already exists
        payment, created = PaymentModel.objects.get_or_create(
            customer=ticket.customer,
            ticket=ticket,
            defaults={"paymentStatus": "Paid"}  # Only set "Paid" if creating a new payment
        )

        if not created:  # If a payment already exists, update its status
            payment.paymentStatus = "Paid"
            payment.save(update_fields=["paymentStatus"])

        return Response(
            {
                "message": "Payment successful.",
                "payment_id": payment.id,
                "payment_status": payment.paymentStatus,  # Verify status
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusModelSerializer:
    pass
@api_view(["GET"])
def customer_search_buses(request):
    from_stop = request.GET.get("fromWhere")
    to_stop = request.GET.get("toWhere")
    date = request.GET.get("date")
    bus_company = request.GET.get("busCompany")

    buses = BusModel.objects.all()

    # Apply filters for date and bus company
    if date:
        buses = buses.filter(date=date)
    if bus_company:
        buses = buses.filter(busCompany=bus_company)

    valid_buses = []

    for bus in buses.distinct():
        route_stops = bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        # Check if fromStop and toStop are in the route, and fromStop comes before toStop
        if from_stop in stop_names and to_stop in stop_names:
            from_index = stop_names.index(from_stop)
            to_index = stop_names.index(to_stop)

            # Only include buses where fromStop comes before toStop
            if from_index < to_index:
                booked_seats = set()
                all_seats = set(range(1, bus.totalSeats + 1))

                # Accumulate booked seats between fromStop and toStop
                for stop in route_stops[from_index:to_index]:
                    booked_seats.update(stop.bookedSeats)

                # Handle blocked seats and compute available seats
                blocked_seats = set(bus.blockedSeats)
                available_seats = sorted(all_seats - booked_seats - blocked_seats)

                # Assign available and booked seats to the bus instance
                bus.bookedSeats = list(booked_seats)
                bus.availableSeats = list(available_seats)

                # Add to valid buses list
                valid_buses.append(bus)

    # Serialize the valid buses
    serializer = BusSerializer(valid_buses, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_book_seat(request):
    try:
        user_model = request.user.profile
        if not user_model:
            return Response({"error": "Only registered customers can book seats."}, status=status.HTTP_403_FORBIDDEN)

        bus_id = request.data.get("bus_id")
        seat_numbers = request.data.get("seat_numbers", [])
        from_stop = request.data.get("from_stop")
        to_stop = request.data.get("to_stop")

        if not bus_id:
            return Response({"error": "Bus ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        bus = get_object_or_404(BusModel, id=bus_id)
        route_stops = bus.routes.order_by("stopOrder")
        stop_names = [stop.stopName for stop in route_stops]

        if from_stop not in stop_names or to_stop not in stop_names:
            return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

        from_index = stop_names.index(from_stop)
        to_index = stop_names.index(to_stop)

        if from_index >= to_index:
            return Response({"error": "Invalid journey selection."}, status=status.HTTP_400_BAD_REQUEST)

        booked_seats = set()
        for stop in route_stops[from_index:to_index]:
            booked_seats.update(stop.bookedSeats)

        if any(seat in booked_seats for seat in seat_numbers):
            return Response({"error": "Some seats are already booked."}, status=status.HTTP_400_BAD_REQUEST)

        ticket = TicketModel.objects.create(
            customer=user_model,
            bus=bus,
            seatNumbers=seat_numbers,
            fromStop=from_stop,
            toStop=to_stop,
        )

        for stop in route_stops[from_index:to_index]:
            stop.bookedSeats.extend(seat_numbers)
            stop.save()

        bus.update_seat_status()

        return Response(
            {"message": "Seat(s) booked successfully.", "ticket_id": ticket.ticketId},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_view_tickets(request):
    tickets = TicketModel.objects.filter(customer=request.user.profile)
    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

