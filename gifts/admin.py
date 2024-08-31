from django.contrib import admin
from .models import Gift,Giftpurchase
from django.contrib.admin.options import ModelAdmin
# Register your models here.


admin.site.register(Gift)

@admin.register(Giftpurchase)
class GiftpurchaseAdmin(ModelAdmin):
    list_display = ['user', 'purchased_on', 'receiver','gift']