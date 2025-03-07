from django.urls import re_path
from GreenBus_App.consumers import BookingConsumer, SeatUpdateConsumer

websocket_urlpatterns = [
    re_path(r'ws/seat-updates/(?P<bus_id>\d+)/$', SeatUpdateConsumer.as_asgi()),
]
