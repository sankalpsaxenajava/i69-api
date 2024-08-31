from django.shortcuts import render

# Create your views here.
from django.views.generic import FormView
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm

from rest_framework.views import APIView
from rest_framework import status
from .serializers import PurchaseSerializer
from rest_framework.response import Response



from user.models import User

class PaypalFormView(FormView):
    template_name = 'paypal_form.html'
    form_class = PayPalPaymentsForm

    def get_initial(self):
        return {
            "business": 'your-paypal-business-address@example.com',
            "amount": 20,
            "currency_code": "EUR",
            "item_name": 'Example',
            "invoice": 1234,
            "notify_url": self.request.build_absolute_uri(reverse('paypal-ipn')),
            "return_url": self.request.build_absolute_uri(reverse('paypal-return')),
            "cancel_return": self.request.build_absolute_uri(reverse('paypal-cancel')),
            "lc": 'EN',
            "no_shipping": '1',
        }

class PaymentDone(APIView):
    def get(self,request):
        return Response({"status":"done"})


class PaymentCancel(APIView):
    def get(self,request):
        return Response({"status":"cancelled"})
