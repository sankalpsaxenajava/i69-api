# middleware.py
from urllib.parse import parse_qs
from channels.auth import AuthMiddlewareStack
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async

@database_sync_to_async
def get_user(token_key):
    try:
        token = Token.objects.get(key=token_key)
        print("token user: ", token.user.username)
        close_old_connections()
        return token.user
    except Token.DoesNotExist:
        print("token user: not found ")
        return AnonymousUser()
    except Exception as e:
        print("token user: some other error: ", e)
    return AnonymousUser()
       
class i69TokenAuthMiddleware():
    """
    Token authorization middleware for Django Channels 3
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            token_key = (dict((x.split('=') for x in scope['query_string'].decode().split("&")))).get('token', None)
            print("token key", token_key)
        except ValueError:
            token_key = None
        scope['user'] = AnonymousUser() if token_key is None else await get_user(token_key)
        print("token user2: ", scope['user'].username)
        return await self.inner(scope, receive, send)

i69TokenAuthMiddlewareStack = lambda inner: i69TokenAuthMiddleware(AuthMiddlewareStack(inner))