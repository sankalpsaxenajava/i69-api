from django.urls import path
from .views import PaypalFormView, PaymentCancel, PaymentDone



urlpatterns=[
    path('payment/', PaypalFormView.as_view()),
    path('payment-done/', PaymentDone.as_view(), name='paypal-return'),
    path('payment-cancelled/', PaymentCancel.as_view(), name='paypal-cancel'),

]