"""framework URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path
from graphene_django.views import GraphQLView as BaseGraphQLView
#from graphene_django.views import GraphQLView
from django.contrib.auth import views as auth_views, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http.response import JsonResponse
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required

from requests_oauthlib import OAuth1
from urllib.parse import urlencode
from rest_framework.views import APIView
from django.http.response import  HttpResponseRedirect
from django.http import HttpResponse
from django.urls import reverse

from django.conf import settings
from django.core.cache import cache
import requests
from rx.linq.observable import throw
from graphql import GraphQLError
from rest_framework.authentication import TokenAuthentication
from user.views import TokenLoginView
from graphene_file_upload.django import FileUploadGraphQLView
from . import views
import datetime

from rest_framework import status
from rest_framework.response import Response

from django_otp.admin import OTPAdminSite
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin

from user.middleware import RequestMiddleware



from . import views

class OTPAdmin(OTPAdminSite):
    pass

# admin.site.__class__ = OTPAdminSite




@login_required
def delete_sessions(request):
    if request.method=='GET':
        request.session.flush()
        return HttpResponseRedirect(reverse('admin:index'))

class TwitterAuthRedirectEndpoint(APIView):
    def get(self, request, *args, **kwargs):
        try:
            oauth = OAuth1(
                      settings.SOCIAL_AUTH_TWITTER_KEY, 
                      client_secret=settings.SOCIAL_AUTH_TWITTER_SECRET
            )
             #Step one: obtaining request token
            request_token_url = "https://api.twitter.com/oauth/request_token"
            data = urlencode({
                      "oauth_callback": settings.SOCIAL_AUTH_TWITTER_CALLBACK_URLS
            })
            response = requests.post(request_token_url, auth=oauth, data=data)
            response.raise_for_status()
            response_split = response.text.split("&")
            oauth_token = response_split[0].split("=")[1]
            oauth_token_secret = response_split[1].split("=")[1]  

                #Step two: redirecting user to Twitter
            twitter_redirect_url = (
              f"https://api.twitter.com/oauth/authenticate?oauth_token={oauth_token}"
            )
            return HttpResponseRedirect(twitter_redirect_url)
        except ConnectionError:
            html="<html><body>You have no internet connection</body></html>"
            return HttpResponse(html, status=403)
        except Exception as e:
            html="<html><body>Something went wrong.Try again." +str(e)+ "</body></html>"
            return HttpResponse(html, status=403)

class TwitterCallbackEndpoint(APIView):
    def get(self, request, *args, **kwargs):
        try:
            oauth_token = request.query_params.get("oauth_token")
            oauth_verifier = request.query_params.get("oauth_verifier")
            oauth = OAuth1(
                                settings.SOCIAL_AUTH_TWITTER_KEY,
                                client_secret=settings.SOCIAL_AUTH_TWITTER_SECRET,
                                resource_owner_key=oauth_token,
                                verifier=oauth_verifier,
            )
            res = requests.post(
                f"https://api.twitter.com/oauth/access_token", auth=oauth
            )
            res_split = res.text.split("&")
            oauth_token = res_split[0].split("=")[1]
            oauth_secret = res_split[1].split("=")[1]
            user_id = res_split[2].split("=")[1] if len(res_split) > 2 else None
            user_name = res_split[3].split("=")[1] if len(res_split) > 3 else None
            #print("User Auth", oauth_token, oauth_secret, user_id, user_name)
            #store oauth_token, oauth_secret, user_id, user_name
            # redirect_url="https: //www.where-to-redirect-users-to"
            # return HttpResponseRedirect(redirect_url)
            return Response(status=status.HTTP_200_OK)
        except ConnectionError:
            return HttpResponse(
                "<html><body>You have no internet connection</body></html>", status=403
            )
        except:
            return HttpResponse(
                "<html><body>Something went wrong.Try again.</body></html>", status=403
            )


class GraphQLView(FileUploadGraphQLView):
    """
        GraphQL view with basic Authorization logic
    """

    
    # operation name for whitelisted mutations, auth token won't be required for this
    WHITELIST_MUTATIONS = ['socialAuth']

    @staticmethod
    def format_error(error):
        formatted_error = super(GraphQLView, GraphQLView).format_error(error)
        # del formatted_error['locations']
        # del formatted_error['path']
        try:
            formatted_error['context'] = error.original_error.context
        except AttributeError:
            pass

        return formatted_error

    def token_auth(self, request):
        """
        Authenticate user session with token
        """
        try:
            tauth = TokenAuthentication()
            request.user, _ = tauth.authenticate(request)
        except Exception as e:
            pass    

    def check_auth_or_readonly(self, request):
        # get operation type and if it is mutation and user is not authenticated raise error
        data = self.parse_body(request)
        query, _, operation_name, _ = self.get_graphql_params(request, data)
        backend = self.get_backend(request)
        print ("query here ...........")
        print (query)
        if query:
            document = backend.document_from_string(self.schema, query)
            operation_type = document.get_operation_type(operation_name)
            document = backend.document_from_string(self.schema, query)
            ast = document.document_ast

            try:
                # check for mutations whitelisted ex- login, signup
                if len(ast.definitions) == 1:
                    operation_definition = ast.definitions[0]
                    name = operation_definition.selection_set.selections[0].name.value
                    if name in GraphQLView.WHITELIST_MUTATIONS:
                        # print(f"skipping auth for user: {name}")
                        return None
            except Exception as e:
                print(e)
            now = datetime.datetime.now()
            cache.set('seen_%s' % (request.user.username), now, settings.USER_LASTSEEN_TIMEOUT)
            a=RequestMiddleware()
            a.process_request(request)
            print(f"queryUser: {request.user}")
            print( operation_type );
            if operation_type.lower() == "mutation" or operation_type.lower() == "query":
                if not get_user_model().objects.filter(id=request.user.id).exists():
                    if 'Authorization' not in request.headers.keys():
                        return JsonResponse({'code':'TokenRequired','errors': [{'message': "Authorization token required"}]}, safe=False)

                    return JsonResponse({'errors': [{'code':'InvalidOrExpiredToken','message': "Authorization token is invalid or expired"}]}, safe=False)
                else:
                    if request.user.is_anonymous:
                        return HttpResponse(status=401, content="Authentication credentials required.",
                                            content_type="application/json")

    def dispatch(self, request, *args, **kwargs):
        self.token_auth(request)
        res = self.check_auth_or_readonly(request)
        if res:
            return res
        return super().dispatch(request, *args, **kwargs)



urlpatterns = [
    
    path('admin/password_change/done/', delete_sessions),
    path('admin/', admin.site.urls),
    #path('admin/password_reset/', auth_views.PasswordResetView.as_view(), name="admin_password_reset",),
    path("admin/password_reset/", views.password_reset_request, name="admin_password_reset",),
    path('admin/password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="../templates/admin/password_reset_done.html"),name="password_reset_done",),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm",),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name="../templates/admin/password_reset_complete.html"), name="password_reset_complete",),

    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path('', include('social_django.urls', namespace='social')),
    path(
        "auth/twitter/redirect/",
        TwitterAuthRedirectEndpoint.as_view(),
        name="twitter-login-redirect",
    ),
    path(
    "signin-twitter/",
        TwitterCallbackEndpoint.as_view(),
        name="twitter-login-callback",
    ),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/token-login/', TokenLoginView.as_view(), name="api_auth_token_login"),
    path('api/user/', include('user.urls'), name="user_app"),
    path('api/worker/', include('user.urls_worker'), name="worker"),
    path('api/', include('defaultPicker.urls'), name="defaultPicker"),
    path('chat/', include('chat.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
admin.site.site_header = 'i69'
admin.site.site_url = ''
admin.empty_value_display = '**Empty**'
admin.site.index_title = 'Admin Dashboard'
admin.site.site_title = 'i69'