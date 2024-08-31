import channels
from django.urls import path
import channels.auth
from django.core.asgi import get_asgi_application

from framework.schema import MyGraphqlWsConsumer
#from .middleware import i69TokenAuthMiddlewareStack

# application = channels.routing.ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": i69TokenAuthMiddlewareStack(
#         channels.routing.URLRouter([
#             path("ws/graphql", MyGraphqlWsConsumer.as_asgi()),
#         ])
#     ),
# })

application = channels.routing.ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": channels.auth.AuthMiddlewareStack(
        channels.routing.URLRouter([
            path("ws/graphql", MyGraphqlWsConsumer.as_asgi()),
        ])
    ),
})