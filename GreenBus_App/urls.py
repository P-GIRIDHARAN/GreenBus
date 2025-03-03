from django.urls import path, include
from rest_framework.routers import DefaultRouter
from GreenBus_App.views import (
    CompanyViewSet, BusViewSet, UserViewSet, TicketViewSet, PaymentViewSet, RouteViewSet,
    login_view, SearchBuses, admin_dashboard, book_seat, cancel_ticket, get_bus_routes, register_user,
    customer_search_buses, customer_book_seat, make_payment, customer_view_tickets
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'buses', BusViewSet)
router.register(r'users', UserViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'routes', RouteViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path("customer/search_buses/", customer_search_buses, name="customer_search_buses"),
    path("customer/book_seat/", customer_book_seat, name="customer_book_seat"),
    path("customer/make_payment/", make_payment, name="customer_make_payment"),
    path("customer/view_tickets/", customer_view_tickets, name="customer_view_tickets"),
    path('api/login/', login_view, name='login'),
    path('api/search-buses/', SearchBuses, name='search-buses'),
    path('api/admin-dashboard/', admin_dashboard, name='admin-dashboard'),
    path('api/book-seat/<int:bus_id>/', book_seat, name='book-seat'),
    path('api/cancel-ticket/<int:ticket_id>/', cancel_ticket, name='cancel-ticket'),
    path('api/get-bus-routes/', get_bus_routes, name='get-bus-routes'),
    path('api/register/', register_user, name='customer-register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
