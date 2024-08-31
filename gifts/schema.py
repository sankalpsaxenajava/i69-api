from dataclasses import fields
from importlib.metadata import requires
from inspect import Arguments
import json
import graphene
from graphene_django import DjangoObjectType
from graphene_django import DjangoListField
from .models import *
from user.models import User
from graphql import GraphQLError
from rest_framework.authtoken.models import Token
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
import django_filters
from user.schema import UserPhotoType
from datetime import datetime
from graphene_file_upload.scalars import Upload
from chat.models import Notification, send_notification_fcm, Room, Message
from chat.schema import OnNewMessage

class GiftType1(DjangoObjectType):
    url = graphene.String()
    class Meta:
        model = Gift
        fields= "__all__"
    def resolve_url(self, info):
        return self.picture.url

class UserType2(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)
    avatar = graphene.Field(UserPhotoType)
    def resolve_avatar(self, info):
        return self.avatar()


class GiftpurchaseType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    class Meta:
        model=Giftpurchase
        fields="__all__"
        filter_fields = {'user__id':['exact'],'receiver__id':['exact']}
        interfaces = (relay.Node,)
    # @property
    # def qs(self):
    #     # The query context can be found in self.request.
    #     return super(GiftpurchaseType, self).qs.order_by("purchased_on")

class GiftpurchaseFilter(django_filters.FilterSet):
    class Meta:
        model = Giftpurchase
        fields = ("user__id", "gift", "receiver__id", "purchased_on")
        #order_by = django_filters.OrderingFilter(fields=(("-purchased_on")))
        order_by = ("-purchased_on", "id",)


class Creategiftmutation(graphene.Mutation):
    class Arguments:
        gift_name=graphene.String(required=True)
        type=graphene.String(required=True)
        cost=graphene.Float(required=True)
        picture=Upload(required=True)

    gift=graphene.Field(GiftType1)

    @classmethod
    def mutate(cls, root, info,gift_name,type,cost,picture):
        new_obj=Gift.objects.create(gift_name=gift_name,type=type,cost=cost,picture=picture)
        new_obj.save()
        return Creategiftmutation(gift=new_obj)

class Deletegiftmutation(graphene.Mutation):
    class Arguments:
        id=graphene.ID(required=True)

    gift=graphene.Field(GiftType1)
    msg=graphene.String()

    @classmethod
    def mutate(cls, root, info, id):
        del_obj=Gift.objects.filter(id=id).first()
        if del_obj:
            del_obj.delete()
            return #Deletegiftmutation(msg="Gift has been deleted.")
        else:
            return GraphQLError("There is no particular gift avaible in gift table with this ID")

class Updategiftmutation(graphene.Mutation):
    class Arguments:
        id=graphene.ID(required=True)
        gift_name=graphene.String(required=True)
        type=graphene.String(required=True)
        cost=graphene.Float(required=True)
        picture=Upload(required=True)

    error=graphene.Boolean()
    msg=graphene.String()
    gift=graphene.Field(GiftType1)

    @classmethod
    def mutate(cls, root, info,id,gift_name,type,cost,picture):
        new_obj=Gift.objects.filter(id=id).first()
        if new_obj:
            new_obj.gift_name=gift_name
            new_obj.type=type
            new_obj.cost=cost
            new_obj.picture=picture
            new_obj.save()
            return Creategiftmutation(gift=new_obj)
        else:
            return GraphQLError("There is no particular gift avaible in gift table with this ID")

class Purchasegiftmutation(graphene.Mutation):
    class Arguments:
        gift_id=graphene.ID()
        receiver_id=graphene.ID()

    error=graphene.Boolean()
    msg=graphene.String()
    gift_purchase=graphene.Field(GiftpurchaseType)

    @classmethod
    def mutate(cls, root, info,gift_id,receiver_id):
        user_obj = info.context.user
        
        if user_obj:
            receiver_obj=User.objects.filter(id=receiver_id).first()
            
            if receiver_obj:
                if receiver_obj==user_obj:
                    raise Exception("You cannot gift yourself")
                gift_obj=Gift.objects.filter(id=gift_id).first()
                
                
                if gift_obj:
                    user_obj.deductCoins(gift_obj.cost)
                    user_obj.save()
                    receiver_obj.gift_coins=int(receiver_obj.gift_coins+gift_obj.cost)
                    receiver_obj.gift_coins_date = datetime.now()
                    receiver_obj.save()
                    gift_purchase_obj=Giftpurchase(user=user_obj,gift_id=gift_id,receiver_id=receiver_id)
                    gift_purchase_obj.save()    
                    notification_obj=Notification(sender=user_obj, user=receiver_obj, notification_setting_id="GIFT RLVRTL")
                    # data = {'coins': str(coins)}
                    # notification_obj.data=data


                    # ----------------- Creating or geting ChatRoom
                    room_name_a = [user_obj.username, receiver_obj.username]
                    room_name_a.sort()
                    room_name_str = room_name_a[0]+'_'+room_name_a[1]

                    try:
                        chat_room = Room.objects.get(name=room_name_str)
                    except Room.DoesNotExist:
                        chat_room = Room(name=room_name_str, user_id=user_obj, target=receiver_obj)
                        chat_room.save()


                    # ----------------- Sending message
                    message = Message(
                        room_id=chat_room,
                        user_id=user_obj,
                        content=f"Sent {gift_obj.gift_name} gift of {gift_obj.cost} coins.",
                    )
                    message.save()

                    chat_room.last_modified = datetime.now()
                    chat_room.save()

                    # ----------------- Sending message notification
                    notification_setting="SNDMSG"
                    app_url=None
                    priority=None
                    icon=None
                    avatar_url = None
                    # checks for avatar_url if None
                    try:
                        avatar_url = user_obj.avatar().file.url
                    except:
                        avatar_url=None
                    data={
                        "roomID":chat_room.id,
                        "notification_type":notification_setting,
                        "message":message.content,
                        "user_avatar":avatar_url,
                        "title":"Sent Gift",
                        "giftUrl":None
                    }
                    if gift_obj.picture:
                        data['giftUrl']=gift_obj.picture.url

                    if avatar_url:
                        icon=info.context.build_absolute_uri(avatar_url)
                    android_channel_id=None
                    notification_obj=Notification(user=receiver_obj, sender=user_obj, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
                    send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
                    OnNewMessage.broadcast(payload=message, group=str(chat_room.target.id))
                    OnNewMessage.broadcast(payload=message, group=str(chat_room.user_id.id))

                    try:
                        send_notification_fcm(notification_obj)
                    except Exception as e:
                        raise Exception(str(e))                    


                    # ----------------- Sending message on receiver side
                    message = Message(
                        room_id=chat_room,
                        user_id=receiver_obj,
                        content=f"Received {gift_obj.gift_name} gift of {gift_obj.cost} coins.",
                    )
                    message.save()

                    chat_room.last_modified = datetime.now()
                    chat_room.save()

                    # ----------------- Sending message notification on receiver side

                    notification_setting = "SNDMSG"
                    app_url = None
                    priority = None
                    icon = None
                    avatar_url = None
                    # checks for avatar_url if None
                    try:
                        avatar_url = receiver_obj.avatar().file.url
                    except:
                        avatar_url = None
                    data = {
                        "roomID": chat_room.id,
                        "notification_type": notification_setting,
                        "message": message.content,
                        "user_avatar": avatar_url,
                        "title": "Received Gift",
                        "giftUrl":None
                    }
                    if gift_obj.picture:
                        data['giftUrl']=gift_obj.picture.url
                        
                    if avatar_url:
                        icon = info.context.build_absolute_uri(avatar_url)
                    android_channel_id = None
                    notification_obj = Notification(user=user_obj, sender=receiver_obj, app_url=app_url,
                                                    notification_setting_id=notification_setting, data=data,
                                                    priority=priority)
                    send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id,
                                          icon=icon)
                    OnNewMessage.broadcast(payload=message, group=str(chat_room.target.id))
                    OnNewMessage.broadcast(payload=message, group=str(chat_room.user_id.id))

                    try:
                        send_notification_fcm(notification_obj)
                    except Exception as e:
                        raise Exception(str(e))
                    return Purchasegiftmutation(gift_purchase=gift_purchase_obj, msg="", error=False)
                        
                else:
                    return Purchasegiftmutation(gift_purchase=None,msg="Gift not exist for particular gift id",error=True)
            else:
                return Purchasegiftmutation(gift_purchase=None,msg="receiver does not exist",error=True)
        else:
            return Purchasegiftmutation(gift_purchase=None,msg="You need to log in first of all ",error=True)
    






# class Currentuseriftmutation(graphene.Mutation):
#     class Arguments:
#         gift_id=graphene.ID()
#         receiver_id=graphene.ID()

#     gift_purchase=graphene.Field(GiftpurchaseType)

#     @classmethod
#     def mutate(cls, root, info,gift_id,receiver_id):
#         user_obj=User.objects.filter(id=info.context.user.id).first()
#         receiver_obj=User.objects.filter(id=receiver_id).first()
#         gift_obj=Gift.objects.filter(id=gift_id).first()
#         if user_obj.purchase_coins>=gift_obj.cost:
#             user_obj.purchase_coins=int(user_obj.purchase_coins-gift_obj.cost)
#             user_obj.save()
#             receiver_obj.gift_coins=int(receiver_obj.gift_coins+gift_obj.cost)
#             receiver_obj.save()
#             gift_purchase_obj=Giftpurchase(user_id=info.context.user.id,gift_id=gift_id,receiver_id=receiver_id)
#             gift_purchase_obj.save()
#             return Purchasegiftmutation(gift_purchase=gift_purchase_obj)
#         else:
#             return GraphQLError("not sufficient coin avaiable in user account")

class Mutation(graphene.ObjectType):
    create_gift= Creategiftmutation.Field()
    delete_gift= Deletegiftmutation.Field()
    update_gift=Updategiftmutation.Field()
    gift_purchase=Purchasegiftmutation.Field()
    
    # current_user_gift=Currentuseriftmutation.Field()

class Query(graphene.ObjectType):
    all_gift=graphene.List(GiftType1)
    all_user_gifts=DjangoFilterConnectionField(GiftpurchaseType, filterset_class=GiftpurchaseFilter)
    all_real_gift=graphene.List(GiftType1)
    all_virtual_gift=graphene.List(GiftType1)
    def resolve_all_real_gift(root,info):
        return Gift.objects.filter(type='real').all()
    def resolve_all_virtual_gift(root,info):
        return Gift.objects.filter(type='virtual').all()

    def resolve_all_gift(root,info):
        return Gift.objects.all()
        
    def resolve_all_user_gifts(root, info, user__id=None, receiver__id=None, **kwargs ):
        if user__id and not receiver__id:
            return Giftpurchase.objects.filter(user=user__id).order_by('-purchased_on')
        if not user__id and receiver__id:
            return Giftpurchase.objects.filter(receiver=receiver__id).order_by('-purchased_on')
        if user__id and receiver__id:
            return Giftpurchase.objects.filter(user=user__id, receiver=receiver__id).order_by('-purchased_on')
        
        

