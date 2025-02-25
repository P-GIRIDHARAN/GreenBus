from django.urls import include, path
from rest_framework.routers import DefaultRouter

from GreenBus_App.views import BusViewSet, UserViewSet, TicketViewSet, PaymentViewSet, SearchBuses

router=DefaultRouter()
router.register(r'buses',BusViewSet)
router.register(r'users',UserViewSet)
router.register(r'tickets',TicketViewSet)
router.register(r'payments',PaymentViewSet)

urlpatterns=[
    path('api/',include(router.urls)),
    path("api/search/", SearchBuses, name="search-api"),

]
