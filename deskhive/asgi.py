"""
ASGI config for deskhive project.
Routes HTTP to Django and WebSocket connections to Channels consumers.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deskhive.settings')

# Initialize Django's ASGI app FIRST, before importing anything that touches models/routing.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import tickets.routing

application = ProtocolTypeRouter({
    # Regular HTTP requests → normal Django (views, DRF, templates)
    "http": django_asgi_app,

    # WebSocket connections → Channels, through auth, to our ticket routing
    "websocket": AuthMiddlewareStack(
        URLRouter(
            tickets.routing.websocket_urlpatterns
        )
    ),
})