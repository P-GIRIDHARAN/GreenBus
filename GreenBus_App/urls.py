from django.urls import include, path
from rest_framework.routers import DefaultRouter

from GreenBus_App.views import BusViewSet, UserViewSet, TicketViewSet, PaymentViewSet, SearchBuses, bus_company_list, \
    CompanyViewSet, cancel_ticket, book_seat, release_seat, RouteViewSet

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
    path("cancel_ticket/<int:ticket_id>/", cancel_ticket, name="cancel_ticket"),
    path("book-seat/<int:bus_id>/", book_seat, name="book-seat"),
    path("release-seat/<int:bus_id>/", release_seat, name="release_seat")
]