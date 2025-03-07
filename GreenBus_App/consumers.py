import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from GreenBus_App.models import BusModel


class BookingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "WebSocket Connected"}))

    async def disconnect(self, close_code):
        pass  # Handle disconnection

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({"message": f"Received: {data}"}))

class SeatUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.bus_id = self.scope["url_route"]["kwargs"]["bus_id"]
        self.group_name = f"bus_{self.bus_id}"

        # Join the WebSocket group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the WebSocket group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def seat_update(self, event):
        # Send seat update message to WebSocket clients
        await self.send(text_data=json.dumps(event["data"]))
