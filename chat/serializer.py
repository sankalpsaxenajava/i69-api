import graphene
from django_filters import FilterSet, OrderingFilter
from graphene import relay
from graphene_django import DjangoObjectType
from django.db.models import Q

from chat.models import * # Room, Message, Broadcasts
from django.contrib.auth import get_user_model

from user.models import ModeratorQue

User = get_user_model()


# class UserFilter(FilterSet):
#     class Meta:
#         model = get_user_model()
#         fields = ('username', "email", "last_name", "first_name", "id",)
#         order_by = ("id",)

class ChatUserType(DjangoObjectType):
    id = graphene.ID(source='pk', required=True)

    class Meta:
        model = User
        fields = ["last_name", "first_name",'username', "email",  "id", "isOnline"]
        interfaces = (relay.Node,)

class ModeratorQueueType(DjangoObjectType):
    class Meta:
        model=ModeratorQue

class RoomFilter(FilterSet):
    class Meta:
        model = Room
        fields = ("last_modified", "name", "user_id", "target")
        order_by = ("-last_modified", "id",)

class RoomType(DjangoObjectType):
    id = graphene.ID(source='pk', required=True)
    unread = graphene.String()
    
    class Meta:
        model = Room
        fields = '__all__'
        interfaces = (relay.Node,)


class NoteType(DjangoObjectType):
    id = graphene.ID(source='pk', required=True)
    unread = graphene.String()

    class Meta:
        model = Notes
        fields = '__all__'
        interfaces = (relay.Node,)


class MessageFilter(FilterSet):
    class Meta:
        model = Message
        fields = ("room_id","user_id", "content", "read", 'timestamp',)
        order_by = ('-timestamp', "id")


class MessageType(DjangoObjectType):
    id = graphene.ID(source='pk', required=True)

    class Meta:
        model = Message
        fields = '__all__'
        interfaces = (relay.Node,)

class MessageStatisticsType(graphene.ObjectType):
    day=graphene.Int()
    received_count=graphene.Int()
    sent_count=graphene.Int()

class SameDayMessageStatisticsType(graphene.ObjectType):
    hour=graphene.Int()
    received_count=graphene.Int()
    sent_count=graphene.Int()

#main
class BroadcastType(graphene.ObjectType):
    broadcast_content = graphene.String()
    broadcast_timestamp = graphene.DateTime()
    unread = graphene.String()

#single thread
class BroadcastMsgsFilter(FilterSet):
    class Meta:
        model = Broadcast
        fields = ("by_user_id","content", "timestamp")
        order_by = ('-timestamp', "id")

class BroadcastMsgsType(DjangoObjectType):
    class Meta:
        model = Broadcast
        fields = '__all__'
        interfaces = (relay.Node,)

#main
class FirstMessageType(graphene.ObjectType):
    firstmessage_content = graphene.String()
    firstmessage_timestamp = graphene.DateTime()
    unread = graphene.String()

#single thread
class FirstMessageMsgsFilter(FilterSet):
    class Meta:
        model = FirstMessage
        fields = ("by_user_id","content", "timestamp")
        order_by = ('-timestamp', "id")

class FirstMessageMsgsType(DjangoObjectType):
    class Meta:
        model = FirstMessage
        fields = '__all__'
        interfaces = (relay.Node,)
