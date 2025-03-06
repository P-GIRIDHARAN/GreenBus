from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.authtoken.admin import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

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
    permission_classes = [IsAuthenticated]  # Allows any logged-in user


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

        UserModel.objects.create(user=user, is_customer=True)

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

@api_view(["POST"])
@permission_classes([AllowAny])
def get_available_seats(request):
    """
    Fetches the available seats for a bus journey between two stops.
    """
    bus_id = request.data.get("busId")
    from_where = request.data.get("fromWhere")
    to_where = request.data.get("toWhere")

    if not bus_id:
        return Response({"error": "busId is required."}, status=400)
    if not from_where or not to_where:
        return Response({"error": "Both fromWhere and toWhere are required."}, status=400)

    try:
        bus = BusModel.objects.get(id=bus_id)
    except BusModel.DoesNotExist:
        return Response({"error": "Bus not found."}, status=404)

    # Fetch the ordered route stops
    route_stops = bus.routes.order_by("stopOrder")
    stop_names = [stop.stopName for stop in route_stops]

    if from_where not in stop_names or to_where not in stop_names:
        return Response({"error": "Invalid stops selected."}, status=400)

    from_index = stop_names.index(from_where)
    to_index = stop_names.index(to_where)

    if from_index >= to_index:
        return Response({"error": "Invalid journey selection."}, status=400)

    booked_seats = set(bus.get_booked_seats(from_where, to_where))
    blocked_seats = set(bus.blockedSeats)
    all_seats = set(range(1, bus.totalSeats + 1))

    # Available seats = Total seats - booked seats (for this segment) - blocked seats
    available_seats = sorted(all_seats - booked_seats - blocked_seats)

    return Response({
        "busId": bus.id,
        "fromWhere": from_where,
        "toWhere": to_where,
        "availableSeats": available_seats
    })



@api_view(["GET"])
def customer_search_buses(request):
    """Search available buses between two stops with correct seat availability."""
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
                booked_seats = set(bus.get_booked_seats(from_stop, to_stop))
                blocked_seats = set(bus.blockedSeats)
                all_seats = set(range(1, bus.totalSeats + 1))

                bus.availableSeats = sorted(all_seats - booked_seats - blocked_seats)
                bus.bookedSeats = sorted(booked_seats)

                valid_buses.append(bus)

    serializer = BusSerializer(valid_buses, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_book_seat(request):
    try:
        user = request.user
        user_model = UserModel.objects.filter(user=user).first()

        if not user_model:
            return Response({"error": "Only registered customers can book seats."}, status=status.HTTP_403_FORBIDDEN)

        bus_id = request.data.get("bus_id")
        seat_numbers = request.data.get("seat_numbers", [])
        from_stop = request.data.get("from_stop")
        to_stop = request.data.get("to_stop")

        if not bus_id:
            return Response({"error": "Bus ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not seat_numbers:
            return Response({"error": "At least one seat must be selected."}, status=status.HTTP_400_BAD_REQUEST)
        if not from_stop or not to_stop:
            return Response({"error": "Both from_stop and to_stop are required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            bus = get_object_or_404(BusModel.objects.select_for_update(), id=bus_id)
            route_stops = bus.routes.order_by("stopOrder")
            stop_names = [stop.stopName for stop in route_stops]

            if from_stop not in stop_names or to_stop not in stop_names:
                return Response({"error": "Invalid stops selected."}, status=status.HTTP_400_BAD_REQUEST)

            from_index = stop_names.index(from_stop)
            to_index = stop_names.index(to_stop)

            if from_index >= to_index:
                return Response({"error": "Invalid journey selection."}, status=status.HTTP_400_BAD_REQUEST)

            # **Fix: Check seat availability only for the requested segment**
            booked_seats = set()
            for stop in route_stops:
                if from_index <= stop.stopOrder < to_index:
                    booked_seats.update(stop.bookedSeats)

            blocked_seats = set(bus.blockedSeats)

            # Ensure no selected seat is already booked
            already_booked = [seat for seat in seat_numbers if seat in booked_seats]
            if already_booked:
                return Response({"error": f"Seats {already_booked} are already booked."}, status=status.HTTP_400_BAD_REQUEST)

            blocked = [seat for seat in seat_numbers if seat in blocked_seats]
            if blocked:
                return Response({"error": f"Seats {blocked} are blocked and cannot be booked."}, status=status.HTTP_400_BAD_REQUEST)

            # **Update RouteModel to mark the seats as booked for the specific segment**
            for stop in route_stops:
                if from_index <= stop.stopOrder < to_index:
                    stop.bookedSeats = list(set(stop.bookedSeats) | set(seat_numbers))
                    stop.save(update_fields=["bookedSeats"])

            # Create the ticket
            ticket = TicketModel.objects.create(
                customer=user_model,
                bus=bus,
                seatNumbers=seat_numbers,
                fromStop=from_stop,
                toStop=to_stop,
            )

        return Response(
            {
                "message": "Seat(s) booked successfully.",
                "ticket_details": {
                    "ticket_id": ticket.ticketId,
                    "bus_no": bus.busNo,
                    "bus_company": bus.busCompany.busCompany,
                    "seat_numbers": seat_numbers,
                    "from_stop": from_stop,
                    "to_stop": to_stop,
                    "journey_date": bus.date.strftime("%Y-%m-%d"),
                    "price": ticket.ticketPrice,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": f"Booking failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_ticket(request):
    try:
        ticket_id = request.data.get("ticket_id")

        ticket = get_object_or_404(TicketModel, ticketId=ticket_id)
        payment = PaymentModel.objects.filter(ticket=ticket).first()

        if not payment:
            return Response({"error": "No payment found for this ticket."}, status=status.HTTP_400_BAD_REQUEST)

        if payment.paymentStatus not in ["Pending", "Paid"]:
            return Response({"error": "Ticket cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        bus = ticket.bus

        bus.release_seats(ticket.seatNumbers)

        # Mark payment as cancelled
        payment.paymentStatus = "Cancelled"
        payment.save(update_fields=["paymentStatus"])

        # Delete the ticket after releasing the seats
        ticket.delete()

        return Response({"message": "Ticket cancelled successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Cancellation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def get_bus_routes(request):
    bus_id = request.data.get("bus_id")
    if not bus_id:
        return Response({"error": "Bus ID is required"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": "Ticket ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        ticket = get_object_or_404(TicketModel, ticketId=ticket_id)

        # Ensure the logged-in user owns the ticket
        if ticket.customer != request.user.profile:
            return Response({"error": "You are not authorized to make payment for this ticket."},
                            status=status.HTTP_403_FORBIDDEN)

        # Check if a payment already exists
        payment, created = PaymentModel.objects.get_or_create(
            customer=ticket.customer,
            ticket=ticket,
            defaults={"paymentStatus": "Paid"}
        )

        if not created:
            if payment.paymentStatus == "Paid":
                return Response(
                    {
                        "message": "Payment has already been made for this ticket.",
                        "payment_id": payment.id,
                        "payment_status": payment.paymentStatus,
                        "ticket_details": {
                            "ticket_id": ticket.ticketId,
                            "bus_no": ticket.bus.busNo,
                            "bus_company": ticket.bus.busCompany.busCompany,
                            "seat_numbers": ticket.seatNumbers,
                            "from_stop": ticket.fromStop,
                            "to_stop": ticket.toStop,
                            "journey_date": ticket.bus.date.strftime("%Y-%m-%d"),
                            "price": ticket.ticketPrice,
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                payment.paymentStatus = "Paid"
                payment.save(update_fields=["paymentStatus"])

        return Response(
            {
                "message": "Payment successful.",
                "payment_id": payment.id,
                "payment_status": payment.paymentStatus,
                "ticket_details": {
                    "ticket_id": ticket.ticketId,
                    "bus_no": ticket.bus.busNo,
                    "bus_company": ticket.bus.busCompany.busCompany,
                    "seat_numbers": ticket.seatNumbers,
                    "from_stop": ticket.fromStop,
                    "to_stop": ticket.toStop,
                    "journey_date": ticket.bus.date.strftime("%Y-%m-%d"),
                    "price": ticket.ticketPrice,
                }
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response({"error": f"Payment failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_view_tickets(request):
    tickets = TicketModel.objects.filter(customer=request.user.profile)
    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

