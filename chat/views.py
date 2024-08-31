from django import forms  
from django.http import JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect, render
from django.forms import fields  
from django.urls import reverse
import os
from user.models import CoinSettings

from time import gmtime, strftime

#from asgiref.sync import async_to_sync, sync_to_async

from chat.models import Room, Message, ChatMessageImages
from user.models import User

class ChatImagesFrm(forms.ModelForm):
    # upload_type = forms.CharField(required=True)
    class Meta:  
        # To specify the model to be used to create form  
        model = ChatMessageImages
        # It includes all the fields of model  
        fields = '__all__'  

def chat_index(request):
    return JsonResponse({"index":"page"}, safe=False)

def image_upload(request):
    print('image upload ', request.user, request.user.is_authenticated)
    if not request.user.is_authenticated:
        return JsonResponse({"success":False,"message":"You need to be logged in"}, safe=False)

    if request.method == 'POST':
        #since we cant use csrf token, this is a simple way of implementing some security
        today = int(strftime("%d", gmtime()))
        yesterday = today - 1
        base_check = 33333333/222
        check_time = []
        check_time.append(int(today * base_check))
        check_time.append(int(yesterday * base_check)) #do we need this?
        print("token: ", str(request.POST.get("token")), str(check_time))

        if not request.POST.get("token"):        
            return JsonResponse({"success":False,"message":"Missing token"}, safe=False)

        if not int(request.POST.get("token")) in check_time:
            return JsonResponse({"success":False,"message":"Invalid token"}, safe=False)

        form = ChatImagesFrm(request.POST, request.FILES)  
        if form.is_valid():  
            user = request.user
            if request.POST.get("upload_type")=="image":
                coins = CoinSettings.objects.filter(method='Photo & file - attached in Chat').first()
                if user.gift_coins+user.purchase_coins<coins.coins_needed:
                    return JsonResponse({"success":False,"message":"Insufficient coins"}, safe=False)
                if coins and coins.coins_needed > 0:
                    user.deductCoins(coins.coins_needed-CoinSettings.objects.filter(method='Message').first().coins_needed)
                    user.save()
            elif request.POST.get("upload_type")=="video":
                coins = CoinSettings.objects.filter(method='VIDEO').first()
                if user.gift_coins+user.purchase_coins<coins.coins_needed:
                    return JsonResponse({"success":False,"message":"Insufficient coins"}, safe=False)
                if coins and coins.coins_needed > 0:
                    user.deductCoins(coins.coins_needed-CoinSettings.objects.filter(method='Message').first().coins_needed)
                    user.save()
            else:
                pass
            # Getting the current instance object to display in the template 
            form.save()
            img_object = form.instance

            return JsonResponse({"img":str(img_object.image.url),"success":True}, safe=False)
        else:
            return JsonResponse({"success":False,"message":form.errors}, safe=False)

    return JsonResponse({"success":False,"message":"No Post"}, safe=False)

