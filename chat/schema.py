import channels
import channels_graphql_ws
import graphene
from django.utils import timezone
from django.utils.timezone import now
from graphene_django.filter import DjangoFilterConnectionField
#from graphql_auth import mutations
#from graphql_auth.schema import MeQuery
#import graphql_jwt
from django.db.models import Q
from django.db.models import OuterRef, Count, Subquery
from django.db.models import Value
from django.db import models
from django.db.models.functions import Coalesce,ExtractDay, ExtractHour

from graphene_django import DjangoObjectType
from django_filters import FilterSet, CharFilter
from datetime import datetime
from graphene import relay
from graphene.types.generic import GenericScalar
from chat.models import *
from chat.serializer import * # ChatUserType, RoomType, RoomFilter, MessageType, MessageFilter, BroadcastsType, BroadcastsFilter
from user.models import CoinSettings

from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser

import logging
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from time import strftime

User = get_user_model()
class NotificationSettingType(DjangoObjectType):
    class Meta:
        model = NotificationSettings
        fields = "__all__"

class NotificationFilter(FilterSet):
    pk = CharFilter(field_name='id', lookup_expr='exact')
    class Meta:
        model= Notification
        fields= []
    @property
    def qs(self):
        # The query context can be found in self.request.
        qs = super(NotificationFilter, self).qs.filter(user=self.request.user)
        qs.update(seen=True)
        return qs.order_by('-created_date')


class NotificationType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    class Meta:
        model = Notification
        filterset_class = NotificationFilter
        fields = ('user','priority','created_date','app_url','sender','seen','notification_setting','notification_body','data',)
        interfaces = (relay.Node,)


class Query( graphene.ObjectType): #MeQuery,
    me = graphene.Field(ChatUserType)

    users = graphene.List(ChatUserType)
    user_search = graphene.List(ChatUserType, search=graphene.String(), 
                                            first=graphene.Int(), 
                                            skip=graphene.Int(),)
    user_name = graphene.List(ChatUserType, name=graphene.String())

    notes = graphene.List(NoteType, room_id=graphene.Int())
    # allnotes = graphene.List(NoteType)

    rooms = DjangoFilterConnectionField(RoomType, filterset_class=RoomFilter)
    room = graphene.Field(RoomType, id=graphene.ID())

    messages = DjangoFilterConnectionField( MessageType, filterset_class=MessageFilter, 
                                            id=graphene.ID(), first=graphene.Int(), skip=graphene.Int(),moderator_id=graphene.String())
    
    messages_statistics=graphene.List(MessageStatisticsType, worker_id=graphene.String(),month=graphene.Int(required=True))
    same_day_messages_statistics=graphene.List(SameDayMessageStatisticsType,worker_id=graphene.String(required=True))
    #
    broadcast = graphene.Field( BroadcastType )

    broadcast_msgs = DjangoFilterConnectionField( BroadcastMsgsType, filterset_class=BroadcastMsgsFilter, 
                                            first=graphene.Int(), skip=graphene.Int(),)

    #
    firstmessage = graphene.Field( FirstMessageType )

    firstmessage_msgs = DjangoFilterConnectionField( FirstMessageMsgsType, filterset_class=FirstMessageMsgsFilter, 
                                            first=graphene.Int(), skip=graphene.Int(),)

    moderators_in_queue=graphene.List(ModeratorQueueType)
    #
    notifications = DjangoFilterConnectionField(NotificationType)
    notification_settings = graphene.List(NotificationSettingType)
    unseen_count = graphene.Int()

    def resolve_unseen_count(root, info):
        return Notification.objects.filter(user=info.context.user, seen=False).count()
        
    def resolve_notification_settings(root, info):
        return NotificationSettings.objects.all()
    @staticmethod
    def resolve_moderators_in_queue(cls,info):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You are not logged in")

        if not user.roles.filter(role__in=['ADMIN','CHATTER']):
            raise Exception("Unauthorized access")


        return ModeratorQue.objects.all()

    @staticmethod
    def resolve_messages_statistics(cls,info,worker_id=None,month=None, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        if user.roles.filter(role__in=['ADMIN']):
            try:
                worker=User.objects.get(id=worker_id)
            except User.DoesNotExist:
                return Exception("Invalid worker_id")
        elif user.roles.filter(role__in=['CHATTER']):
            worker=user
        else:
            raise Exception("You must be ADMIN or CHATTER to access this API")

        m=Message.objects.filter(
            Q(timestamp__month=month,sender_worker=worker)|Q(timestamp__month=month,receiver_worker=worker)
        ).annotate(
            day=ExtractDay('timestamp'),
        ).values(
            'day'
        ).annotate(
            sent_count=Count('sender_worker')
        ).annotate(
            received_count=Count('receiver_worker')
        ).order_by('day').values("day","sent_count","received_count")
        return m

    @staticmethod
    def resolve_same_day_messages_statistics(cls,info,worker_id=None,**kwargs):
        # user= user = info.context.user
        # if not (list(user.roles.all().values_list("role")) == [('REGULAR',), ('CHATTER',)]):
        #     return Exception("Invalid user")
        
        try:
            worker=User.objects.get(id=worker_id)
        except User.DoesNotExist:
            return Exception("Invalid worker_id")

        day=timezone.datetime.today().day
        stats=Message.objects.filter(
            Q(timestamp__day=day,sender_worker=worker)|Q(timestamp__day=day,receiver_worker=worker)
        ).annotate(
            hour=ExtractHour('timestamp'),
        ).values(
            'hour'
        ).annotate(
            sent_count=Count('sender_worker')
        ).annotate(
            received_count=Count('receiver_worker')
        ).order_by('hour').values("hour","sent_count","received_count")

        return stats



    @staticmethod
    def resolve_users(self, info):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        return get_user_model().objects.all()

    @staticmethod
    def resolve_user_search(self, info, search=None, first=None, skip=None, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        qs = get_user_model().objects.all()
        
        if search:
            qs = qs.filter(username__icontains=search)

        if skip:
            qs = qs[skip:]

        if first:
            qs = qs[:first]

        return qs

    @staticmethod
    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Not logged in!')

        return user

    @staticmethod
    def resolve_rooms(cls, info, **kwargs): 
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        #unread all except sent by me;
        if user.fake_users.all().count()>0:
            fake_users=user.fake_users.all()
            user_rooms = (Room.objects.filter(Q(user_id__in=fake_users) | Q(target__in=fake_users)).exclude(Q(user_id__in=fake_users,deleted=1) | Q(target__in=fake_users,deleted=2)).order_by('-last_modified')
            .annotate(unread=Coalesce(Subquery(Message.objects.filter(room_id=OuterRef('pk'),read__isnull=True).exclude(user_id__in=fake_users).values('room_id').annotate(count=Count('pk')).values('count'), output_field=models.IntegerField(default=0)),Value(0))))
        else:   
            user_rooms = (Room.objects.filter(Q(user_id=user) | Q(target=user)).exclude(Q(user_id=user,deleted=1) | Q(target=user,deleted=2)).order_by('-last_modified')
                .annotate(unread=Coalesce(Subquery(Message.objects.filter(room_id=OuterRef('pk'),read__isnull=True).exclude(user_id=user).values('room_id').annotate(count=Count('pk')).values('count'), output_field=models.IntegerField(default=0)),Value(0))))
        # user_rooms = (Room.objects.filter(Q(user_id=user) | Q(target=user)).order_by('-last_modified')
        #     .annotate(unread=Coalesce(Subquery(Message.objects.filter(room_id=OuterRef('pk'),read__isnull=True).exclude(user_id=user).values('room_id').annotate(count=Count('pk')).values('count'), output_field=models.IntegerField(default=0)),Value(0))))

        return user_rooms

    # ~ New 
    @staticmethod
    def resolve_broadcast(cls, info, **kwargs):
        # added on top of rooms.
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        deleted_upto = user.broadcast_deleted_upto if user.broadcast_deleted_upto is not None else 0
        read_upto   = user.broadcast_read_upto if user.broadcast_read_upto is not None else 0

        print("deleted_upto", deleted_upto)

        broadcast = Broadcast.objects.filter(id__gt=deleted_upto).order_by("timestamp").last()
        unread = Broadcast.objects.filter(id__gt=read_upto).count()
        broadcast_str = ''
        broadcast_time = ''
        if broadcast:
            broadcast_str = broadcast.content
            broadcast_time = user.created_at

        return BroadcastType( broadcast_content=broadcast_str, broadcast_timestamp=broadcast_time, unread=int(unread))

    @staticmethod
    def resolve_broadcast_msgs(cls, info, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        deleted_upto = user.broadcast_deleted_upto if user.broadcast_deleted_upto is not None else 0

        user.broadcast_read_upto = Broadcast.objects.last().id
        user.save()

        broadcast = Broadcast.objects.filter(id__gt=deleted_upto).order_by("-timestamp")
        return broadcast

    # ~ New 
    @staticmethod
    def resolve_firstmessage(cls, info, **kwargs):
        # added on top of rooms.
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        read_upto   = user.firstmessage_read_upto if user.firstmessage_read_upto is not None else 0

        firstmessage = FirstMessage.objects.last()
        unread = FirstMessage.objects.filter(id__gt=read_upto).count()
        firstmessage_str = ''
        firstmessage_time = ''
        if firstmessage:
            firstmessage_str = firstmessage.content
            firstmessage_time = user.created_at

        return FirstMessageType( firstmessage_content=firstmessage_str, firstmessage_timestamp=firstmessage_time, unread=int(unread))

    @staticmethod
    def resolve_firstmessage_msgs(cls, info, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        user.firstmessage_read_upto = FirstMessage.objects.last().id
        user.save()

        firstmessage = FirstMessage.objects.all().order_by("-timestamp")
        return firstmessage

    @staticmethod
    def resolve_notes(cls, info, room_id, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")
        roles = [r.role for r in user.roles.all()]
        if "REGULAR" not in roles and "CHATTER" not in roles:
            raise Exception("The user is not worker")
        
        fake_users=user.fake_users.all()
        room=Room.objects.filter(Q(id=room_id,user_id__in=fake_users) | Q(id=room_id,target__in=fake_users)).exclude(Q(id=room_id,user_id__in=fake_users,deleted=1) | Q(id=room_id,target__in=fake_users,deleted=2))
        if room:
            room=room[0]
        else:
            raise Exception("Room not found")
            
        return Notes.objects.filter(room_id=room_id)

    @staticmethod
    def resolve_room(cls, info, id, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        return Room.objects.get(id=id)

    @staticmethod
    def resolve_user_name(cls, info, name, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("'Not logged in!'")
        # query = "Select * from User where fullName like '%{}%'".format(name)
        # print("query here ")
        # print(query)
        # return User.objects.raw(query)
        return User.objects.filter(fullName__icontains=name)




    # result = table.objects.filter(string__contains='pattern')

    @staticmethod
    def resolve_messages(cls, info, id, skip=None, last=None, moderator_id=None, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")
        
        if moderator_id:  # if message sent my moderator then set user to moderator user.
            if not user.fake_users.filter(id=moderator_id).exists():
                raise Exception("Invalid moderator id")
            user=User.objects.get(id=moderator_id)
        
        room = Room.objects.get(id=id)
        if user != room.user_id and user != room.target:
            raise Exception('You are not allowed to view this chat')

        #read all except sent by me;
        Message.objects.filter(room_id=room,read__isnull=True).exclude(user_id=user).update(read=datetime.now())
        #return Message.objects.filter(room_id=room).order_by('timestamp')
        qs = Message.objects.filter(room_id=room).order_by('-timestamp')
        if skip:
            qs = qs[skip:]

        if last:
            qs = qs[:last]

        return qs

class CreateChat(graphene.Mutation):
    """
    to creeate a chat you need to pass `user_name`
    """
    room = graphene.Field(RoomType)
    error = graphene.String()

    class Arguments:
        user_name = graphene.String(required=True)
        moderator_id = graphene.String(required=False)
    @classmethod
    def mutate(cls, _, info, user_name=None,moderator_id=None):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        try:
            target_user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            raise Exception("User name not found")

        # if user.id != moderator_id:
        #     raise Exception("User is not moderator.")

        if user.fake_users.all().count()>0:
            if not moderator_id:
                raise Exception("moderator_id required")

            if not user.fake_users.filter(id=moderator_id).exists():
                raise Exception("Invalid moderator id")

            user=User.objects.get(id=moderator_id)

            if target_user.roles.filter(role="MODERATOR").exists():
                raise Exception("Can not chat Moderator with Moderator")

        if user.username == user_name:
            raise Exception("You can not chat with yourself.")

        if user.blockedUsers.exclude(blocked_by=target_user).count() > 0:
            raise Exception("This User no longer accepts PMs.")

        room_name_a = [user.username, user_name]
        room_name_a.sort()
        room_name_str = room_name_a[0]+'_'+room_name_a[1]

        try:
            chat_room = Room.objects.get(name=room_name_str)
        except Room.DoesNotExist:
            chat_room = Room(name=room_name_str, user_id=User.objects.get(id=user.id), target=target_user)
            chat_room.save()

        return CreateChat(room=chat_room)


class CreateNotes(graphene.Mutation):
    """
    to creeate notes you need to pass `room id and content`
    """
    notes = graphene.Field(NoteType)
    error = graphene.String()

    class Arguments:
        room_id = graphene.Int(required=True)
        content = graphene.String(required=True)
        forRealUser = graphene.Boolean(required=True)
    @classmethod
    def mutate(cls, _, info, room_id=None,content=None, forRealUser=None):

        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")
        
        roles = [r.role for r in user.roles.all()]
        if "REGULAR" not in roles and "CHATTER" not in roles:
            raise Exception("The user is not worker")

        fake_users=user.fake_users.all()
        room=Room.objects.filter(Q(id=room_id,user_id__in=fake_users) | Q(id=room_id,target__in=fake_users)).exclude(Q(id=room_id,user_id__in=fake_users,deleted=1) | Q(id=room_id,target__in=fake_users,deleted=2))
        if room:
            room=room[0]
        else:
            raise Exception("Room not found")
            
        notes = Notes.objects.get_or_create(room_id=room, forRealUser=forRealUser)
        notes[0].content = content
        notes[0].save()
        return CreateNotes(notes=notes[0])


class SendMessage(graphene.Mutation):
    message = graphene.Field(MessageType)
    #message = graphene.String()

    class Arguments:
        message_str = graphene.String(required=True)
        room_id = graphene.Int(required=True)
        moderator_id = graphene.String()

    @classmethod
    def mutate(cls, _, info, message_str, room_id,moderator_id=None):
        user = info.context.user
        roles = [r.role for r in user.roles.all()]
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        room = Room.objects.get(pk=room_id)
        worker=None
        if moderator_id:  # if message sent my moderator then set user to moderator user.
            if not user.fake_users.filter(id=moderator_id).exists():
                raise Exception("Invalid moderator id")
            worker=user            
            user=User.objects.get(id=moderator_id)

        if user != room.user_id and user != room.target:
            raise Exception('You are not allowed to post or view this chat')

        if user == room.user_id:
            user_for_notification=room.target
            _d = user.blockedUsers.filter(username=room.target).exists()
            if _d == True:
                raise Exception("This User no longer accepts DMs.")

        if user == room.target:
            user_for_notification=room.user_id
            _d = user.blockedUsers.filter(username=room.user_id).exists()
            if _d == True:
                raise Exception("This User no longer accepts DMs..")

        if room.deleted > 0:
            room.deleted = 0
            room.save()
        if "REGULAR" not in roles and "CHATTER" not in roles:
            messages = Message.objects.filter(room_id_id=room.id)
            if messages.count() > 0:
                coins = CoinSettings.objects.filter(method='Message').first()
                if coins and coins.coins_needed > 0:
                    user.deductCoins(coins.coins_needed)
                    user.save()
                else:
                    raise Exception("Not enough coins.")
        message = Message(
                room_id=room,
                user_id=user,
                content=message_str,
            )
        
        if user.roles.filter(role="MODERATOR"):
            message.sender_worker=worker
        elif room.target.roles.filter(role="MODERATOR") or room.user_id.roles.filter(role="MODERATOR"):
            if room.user_id==user:
                message.receiver_worker=room.target.owned_by.all()[0]
            else:
                message.receiver_worker=room.user_id.owned_by.all()[0]

        message.save()

        room.last_modified = datetime.now()
        room.save()

        #user last online
        user.last_login=datetime.now()
        user.save()
    # if room.user_id == user:
    #     OnNewMessage.broadcast(payload=message, group=room.target.username)
    # else:
    #     OnNewMessage.broadcast(payload=message, group=room.user_id.username)
    #
    #     data = {
    #         "roomIDs": room_id,
    #         "notification_type": "chat_notification",
    #         "message": message_str,
    #         "user_avatar": "test url",
    #     }
        # SendNotification( user_id=moderator_id, data=data)
        notification_setting="SNDMSG"
        app_url=None
        priority=None
        icon=None
        avatar_url = None
        # checks for avatar_url if None
        try:
            avatar_url = user.avatar().file.url
        except:
            avatar_url=None
        data={
            "roomID":room.id,
            "notification_type":notification_setting,
            "message":message.content,
            "user_avatar":avatar_url,
            "title":"Sent message"
        }
        if avatar_url:
            icon=info.context.build_absolute_uri(avatar_url)
        android_channel_id=None
        notification_obj=Notification(user=user_for_notification, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        OnNewMessage.broadcast(payload=message, group=str(room.target.id))
        OnNewMessage.broadcast(payload=message, group=str(room.user_id.id))
        #below not working for some reason, we broadcast to both.
        return SendMessage(message=message)


class OnNewMessage(channels_graphql_ws.Subscription):
    message = graphene.Field(MessageType)
    notification_queue_limit = 64

    class Arguments:
        token = graphene.String()
        moderator_id = graphene.String()

    def subscribe(cls, info, token, moderator_id=None):
        #user = info.context.user

        try:
            token = Token.objects.get(key=token)
            print("token user schema: ", token.user.username)
            user = token.user
            user.last_login=datetime.now()
            user.save()
            if user.fake_users.all().count()>0:
                if moderator_id:
                    if not user.fake_users.filter(id=moderator_id).exists():
                        raise Exception("Invalid moderator_id")
                    user=User.objects.get(id=moderator_id)
                    user.last_login=datetime.now()
                    user.save()
                else:
                    raise Exception("moderator_id required")

        except Token.DoesNotExist:
            print("token user schema: not found ")
            user = AnonymousUser()

        return [str(user.id)] if user is not None and user.is_authenticated else []

    def publish(self, info, token=None, moderator_id=None):
        message = Message.objects.get(id=self.id)
        return OnNewMessage(
            message=message

        )

class SendNotification(graphene.Mutation):
    class Arguments:
        notification_setting = graphene.String()
        icon = graphene.String(required=False)

        user_id = graphene.UUID(required=True)
        app_url =graphene.String()
        priority = graphene.Int()
        data = GenericScalar()
        android_channel_id = graphene.String()

    sent = graphene.Boolean()

    def mutate(root, info,notification_setting, user_id, icon=None, app_url=None, priority=None, data=None, android_channel_id=None):

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise Exception('User with this ID does not exist.')
        print("this is the payload ......")
        print(data)
        notification_obj=Notification(user=user, sender=info.context.user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        print ("notification_obj")
        print (notification_obj)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        return SendNotification(sent=True)
        
class DeleteBroadcast(graphene.Mutation):
    broadcast=graphene.Field(BroadcastType)
    message=graphene.String()
    success=graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        del_obj=Broadcast.objects.last()
        if del_obj:
            user.broadcast_deleted_upto = del_obj.id
            user.save()
            return DeleteBroadcast(success=True, message="Broadcast has been deleted.")
        else:
            return GraphQLError("There is no Broadcast")

class DeleteMessages(graphene.Mutation):
    message=graphene.String()
    success=graphene.Boolean()

    class Arguments:
        room_id = graphene.Int(required=True)

    @classmethod
    def mutate(cls, root, info, room_id, **kwargs):
        user = info.context.user
        if user is None or not user.is_authenticated:
            raise Exception("You need to be logged in to chat")

        room = Room.objects.get(pk=room_id)

        if user != room.user_id and user != room.target:
            raise Exception('You are not allowed to post or view this chat')

        if (room.deleted == 0 or room.deleted == 1 ) and user == room.user_id:
            room.deleted = 1
            room.save()
        elif ( room.deleted == 0 or room.deleted == 2 ) and user == room.target:
            room.deleted = 2
            room.save()
        elif room.deleted > 0:
            room.delete()

        return DeleteMessages(success=True, message="Messages have been deleted.")

class Mutation(graphene.ObjectType):
    send_message = SendMessage.Field()
    create_chat = CreateChat.Field()
    create_notes = CreateNotes.Field()
    sendNotification = SendNotification.Field()
    delete_broadcast = DeleteBroadcast.Field()
    delete_messages = DeleteMessages.Field()
    # token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    # verify_token = graphql_jwt.Verify.Field()
    # refresh_token = graphql_jwt.Refresh.Field()

class Subscription(graphene.ObjectType):
    on_new_message = OnNewMessage.Field()
