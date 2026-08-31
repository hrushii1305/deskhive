from django.urls import re_path
from . import consumers

# WebSocket URL patterns — like urls.py, but for WebSocket connections.
# A client connecting to ws://.../ws/tickets/<id>/ is routed to TicketConsumer.
websocket_urlpatterns = [
    re_path(r'ws/tickets/(?P<ticket_id>\d+)/$', consumers.TicketConsumer.as_asgi()),
]