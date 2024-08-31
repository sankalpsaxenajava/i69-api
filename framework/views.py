from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordResetForm

from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
import sys
from user.models import User, UserSocialProfile, CoinsHistory
from django.http import JsonResponse
from rest_framework import status

def get_user_totp_device(user, confirmed=None):
    devices = devices_for_user(user, confirmed=confirmed)
    for device in devices:
        if isinstance(device, TOTPDevice):
            return device


def create_device_topt_for_user(user):
    device = get_user_totp_device(user)
    if not device:
        device = user.totpdevice_set.create(confirmed=False)
    return device.config_url
    
def validate_user_otp(user, otp_token):
    device = get_user_totp_device(user)
    if device is None:
        return dict(res=False, data='No device registered.')
    elif not device == None and device.verify_token(otp_token):
        if not device.confirmed:
            device.confirmed = True
            device.save()
            return dict(res=True, data='Successfully confirmed and saved device..')
        else:
            return dict(res=True, data="OTP code has been verified.")
    else:
        return dict(res=False, data='The code you entered is invalid')
        
def password_reset_request(request):
    """this is password reset override"""
    err = msg = ''
    if request.method == "POST":
        otp_token = request.POST['otp_token']
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid() and otp_token:
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    create_device_topt_for_user(user=user)
                    ret = validate_user_otp(user, otp_token)
                    
                    if ret['res'] == True:
                        msg = ret['data']
                        subject = "Password Reset Requested"
                        email_template_name = "../templates/admin/password_reset_email.txt"
                        c = {
                            "email":user.email,
                            'domain':'127.0.0.1:8000',
                            'site_name': 'Website',
                            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                            "user": user,
                            'token': default_token_generator.make_token(user),
                            'protocol': 'http',
                        }
                        email = render_to_string(email_template_name, c)
                        try:
                            send_mail(subject, email, 'admin@example.com' , [user.email], fail_silently=False)
                        except BadHeaderError:
                            return HttpResponse('Invalid header found.')
                        return redirect("/admin/password_reset/done/")
                    else:
                        err = ret['data']

    password_reset_form = PasswordResetForm()
    return render(request=request, template_name="../templates/admin/password_reset.html", context={"password_reset_form":password_reset_form, 'err': err})

def password_reset_complete(request):
    """this is password reset override"""
    err = msg = ''
    return render(request=request, template_name="../templates/admin/password_reset_complete.html")


