from django.urls import include, path
from rest_framework.routers import DefaultRouter

from GreenBus_App.views import BusViewSet, UserViewSet, TicketViewSet, PaymentViewSet, SearchBuses, bus_company_list, \
    CompanyViewSet, cancel_ticket, book_seat, RouteViewSet

router=DefaultRouter()
router.register(r'buses',BusViewSet)
router.register(r'users',UserViewSet)
router.register(r'tickets',TicketViewSet)
router.register(r'payments',PaymentViewSet)
router.register(r'company',CompanyViewSet)
router.register(r'routes',RouteViewSet)
urlpatterns=[
    path('api/',include(router.urls)),
    path('api/search/', SearchBuses, name="search-api"),
    path("api/company/<int:company_id>/buses/", bus_company_list, name="company-buses"),
    path("api/cancel-ticket/<int:ticket_id>/", cancel_ticket, name="cancel-ticket"),
    path("api/book-seat/<int:bus_id>/", book_seat, name="book-seat"),
]