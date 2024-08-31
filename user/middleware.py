import threading
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authentication import TokenAuthentication

class RequestMiddleware(MiddlewareMixin):

    thread_local = threading.local()

    def process_request(self, request):
        RequestMiddleware.thread_local.current_user = request.user

class TokenAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            tauth = TokenAuthentication()
            request.user, _ = tauth.authenticate(request)
            request.user.last_seen=datetime.datetime.now()
            request.user.save() 
        except Exception as e:
            pass