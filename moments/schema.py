# from typing_extensions import Required
import os
from calendar import monthcalendar
from dataclasses import field
from inspect import Arguments
from django.conf import settings
# from typing_extensions import Required
import graphene
from graphene_django import DjangoObjectType
from graphene_django import DjangoListField
from httpx import request
from .models import *
from graphene_file_upload.scalars import Upload
from rest_framework.authtoken.models import Token
import mimetypes
import datetime
import threading
import cv2
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pathlib import Path
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
import tempfile
from django_filters import FilterSet, OrderingFilter, CharFilter
from user.schema import UserPhotoType
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from pathlib import Path
from django.core.files.storage import default_storage
from .tasks import createThumbnail
from chat.models import Notification, send_notification_fcm

EXPIRE_TIME =  24 #hours


class UserTypeone(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)
    avatar = graphene.Field(UserPhotoType)
    def resolve_avatar(self, info):
        return self.avatar()

class GenericLikeType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    class Meta:
        model=GenericLike
        filter_fields={}
        fields = '__all__'
        interfaces = (relay.Node,)

class GenericReplyType(DjangoObjectType):
    pk = graphene.Int(source='pk')

    class Meta:
        model=GenericComment
        filter_fields={}
        fields = '__all__'
        interfaces = (relay.Node,)

class GenericCommentType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    replys = DjangoFilterConnectionField(GenericReplyType)
    class Meta:
        model=GenericComment
        filter_fields={}
        fields = '__all__'
        interfaces = (relay.Node,)
    

    def resolve_replys(self, info):
        return self.comments.all().order_by("-created_date")

class ReplyType(DjangoObjectType):
    class Meta:
        model= Comment
        filter_fields=('reply_to',)
        fields= ('id','user','momemt','comment_description', 'created_date', 'reply_to')
        interfaces = (relay.Node,)

class CommentFilter(FilterSet):
    pk = CharFilter(field_name='id', lookup_expr='exact')
    class Meta:
        model= Comment
        fields= ['momemt__id','id',]
    @property
    def qs(self):
        # The query context can be found in self.request.
        return super(CommentFilter, self).qs.filter(reply_to=None).order_by('-created_date')
    
class CommentType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    class Meta:
        model= Comment
        fields= ('id','user','momemt','comment_description', 'created_date')
        filterset_class = CommentFilter
        interfaces = (relay.Node,)
    # replys = DjangoFilterConnectionField(ReplyType)
    replys = graphene.List(ReplyType)
    like = graphene.Int()
    def resolve_like(self, info):
        return CommentLike.objects.filter(comment=self).count()

    def resolve_replys(self,info):
        return Comment.objects.filter(reply_to=self).order_by('-created_date')

class MomentFilter(FilterSet):
    pk = CharFilter(field_name='id', lookup_expr='exact')
    class Meta:
        model= Moment
        fields= ['user__id','id',]
    @property
    def qs(self):
        # The query context can be found in self.request.
        return super(MomentFilter, self).qs.order_by("-created_date")

class MomentsTyps(DjangoObjectType):
    pk = graphene.Int(source='pk')
    class Meta:
        model= Moment
        fields=('id','Title','file','created_date','user','moment_description')
        filterset_class = MomentFilter
        interfaces = (relay.Node, )
    user = graphene.Field(UserTypeone)
    like = graphene.Int()
    comment = graphene.Int()
    moment_description_paginated = graphene.List(graphene.String, width=graphene.Int(), character_size=graphene.Int())


    def resolve_moment_description_paginated(self, info, width=None, character_size=None):
        
        try:
            max_length = int(width/character_size)

            description_length = len(self.moment_description)
            
            if max_length >= description_length:
                return [self.moment_description]
            char = None
            while max_length > 0:
                
                if char == ' ':
                    max_length = max_length+1

                    break
                char = self.moment_description[max_length]
                max_length = max_length-1
            desc_list = []
            desc_list.append(f"{self.moment_description[0:max_length]}")
            desc_list.append(self.moment_description[max_length:description_length-1])
            return desc_list
        except Exception as e:
            print(e)
            return [self.moment_description]

        


    def resolve_like(self, info):
        return Like.objects.filter(momemt=self).count()
    
    def resolve_comment(self, info):
        return Comment.objects.filter(momemt=self, reply_to=None).count()

class StoryFilter(FilterSet):
    pk = CharFilter(field_name='id', lookup_expr='exact')
    class Meta:
        model= Story
        fields= ['user__id','id',]
    @property
    def qs(self):
        # The query context can be found in self.request.
        try:
            visible_time = StoryVisibleTime.objects.all().first()
            hours=visible_time.hours+visible_time.days*24+visible_time.weeks*7*24
            
        except:
            hours = 24
        return super(StoryFilter, self).qs.filter(created_date__gte=datetime.datetime.now()-datetime.timedelta(hours=hours)).order_by('-created_date')


class StoryType(DjangoObjectType):
    pk = graphene.Int(source='pk')
    likes = DjangoFilterConnectionField(GenericLikeType)
    likes_count = graphene.Int()
    comments_count = graphene.Int()
    comments = DjangoFilterConnectionField(GenericCommentType)
    class Meta:
        model = Story
        fields = '__all__'
        interfaces = (relay.Node,)
        filterset_class=StoryFilter
    user = graphene.Field(UserTypeone)
    file_type  = graphene.String()

    def resolve_likes_count(self, info):
        return self.likes.all().count()
    def resolve_comments_count(self, info):
        return self.comments.all().count()

    def resolve_likes(self, info):
        return self.likes.all()
    def resolve_comments(self, info):
        return self.comments.all().order_by("-created_date")

    def resolve_file_type(self, info):
        if self.file:
            file_type,t =mimetypes.guess_type(str(self.file))
            return file_type.split('/')[0]
        return "unknown"





class LikeType(DjangoObjectType):
    class Meta:
        model = Like
        fields = ('id','user','momemt')
    
class CommentLikeType(DjangoObjectType):
    class Meta:
        model = CommentLike
        fields = '__all__'
    
    


class ReportType(DjangoObjectType):
    class Meta:
        model = Report
        fields = ('id','user','momemt','Report_msg')

class Momentmutation(graphene.Mutation):
    class Arguments:
        user=graphene.String(required=True)
        Title=graphene.String(required=True)
        moment_description=graphene.String(required=True)
        file = Upload(required=True)
        moderator_id = graphene.String(required=False)
        # moment_description=graphene.String(required=True)

    moment=graphene.Field(MomentsTyps)

    @classmethod
    def mutate(cls,root,info,Title, moment_description, file, user,moderator_id=None):
        try:
            muser = info.context.user

            if moderator_id:  # if request sent my moderator then set user to moderator user.
                roles = [r.role for r in muser.roles.all()]
                if "ADMIN" in roles or "CHATTER" in roles or "REGULAR" in roles:
                    if not muser.fake_users.filter(id=moderator_id).exists():
                        raise Exception("Invalid moderator id")
                    muser = User.objects.filter(id=moderator_id).first()
                else:
                    return Exception("User cannot create moderator story")
            new_moment = Moment(user=muser,Title=Title,moment_description=moment_description,file=file)
            new_moment.save()
            return Momentmutation(moment=new_moment)
            
        except Exception as e:
            raise Exception(str(e))

# def createThumbnail(**kwargs):
#     file=kwargs['file']
#     story=kwargs['story']
#     print(file)
#     print(story)
#     with tempfile.NamedTemporaryFile(mode="wb") as vid:
                
                
#                 vidcap = cv2.VideoCapture(story.file.path)
                
#                 success,image = vidcap.read()
                
#                 if success:
#                     _, img = cv2.imencode('.jpeg', image)
#                     img.tobytes()
#                     file = ContentFile(img)
#                     story.thumbnail.save('thumbnail.jpeg', file , save=True)
#                     return
 

class Storymutation(graphene.Mutation):
    class Arguments:
        file=Upload(required=True)
        moderator_id = graphene.String(required=False)


    story=graphene.Field(StoryType)

    @classmethod
    def mutate(cls,root,info,file,moderator_id=None):
        # print(request.user)
        
        user = info.context.user
        if moderator_id:  # if request sent my moderator then set user to moderator user.
            roles = [r.role for r in user.roles.all()]
            if "ADMIN" in roles or "CHATTER" in roles or "REGULAR" in roles:
                if not user.fake_users.filter(id=moderator_id).exists():
                    raise Exception("Invalid moderator id")
                user = User.objects.filter(id=moderator_id).first()
            else:
                return Exception("User cannot create moderator story")

        new_story = Story(user=user, file=file)
        file_type, t =mimetypes.guess_type(str(file))
        if file_type.split('/')[0] == "video":
            thumbnail = default_storage.open('static/thumbnail.png')
            new_story.thumbnail.save('thumbnail.jpeg', thumbnail , save=True)
            createThumbnail.delay(new_story.id)
            return Storymutation(story=new_story)
        new_story.save() 
        return Storymutation(story=new_story)

        

class Momentdeletemutation(graphene.Mutation):
    class Arguments:
        id=graphene.ID()

    moment=graphene.Field(MomentsTyps)

    @classmethod
    def mutate(cls,root,info,id):
        # print(request.user)
        try:
            delete_moment=Moment.objects.filter(id=id).first()
            delete_moment.delete()
            return "delete successfully"
        except:
            raise Exception("invalid moment id")

class Momentlikemutation(graphene.Mutation):
    class Arguments:
        # user=graphene.String(required=True)
        moment_id=graphene.ID()

    like=graphene.Field(LikeType)

    @classmethod
    def mutate(cls,root,info,moment_id):
        
        user = info.context.user
        try:
            moment=Moment.objects.get(id=moment_id)
        except Moment.DoesNotExist:
            return Exception("Invalid moment_id")

        like=Like.objects.filter(user=user, momemt_id=moment_id)
        if like.exists():
            like=like[0]
            like.delete()
            return Momentlikemutation(like=like)
        new_like=Like(user=user, momemt_id=moment_id)
        new_like.save()
        # new_like.save()
        # TODO: set data payload, user avtar as icon
        data={}
        priority=None
        icon=None
        app_url=None
        android_channel_id=None
        notification_setting="LIKE"

        notification_obj=Notification(user=moment.user, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        
        return Momentlikemutation(like=new_like)

class CommentLikeMutation(graphene.Mutation):
    class Arguments:
        comment_id = graphene.String()
    
    comment_like=graphene.Field(CommentLikeType)
    @classmethod
    def mutate(cls,root,info,comment_id):
        user = info.context.user
        commentlike=CommentLike.objects.filter(user=user, comment_id=comment_id)
        if commentlike.exists():
            commentlike=commentlike[0]
            commentlike.delete()
            return CommentLikeMutation(commentlike)

        new_commentlike=CommentLike(user=user, comment_id=comment_id)
        new_commentlike.save()
        notification_to=new_commentlike.comment.user

        # TODO: set data payload, user avtar as icon
        data={}
        priority=None
        icon=None
        app_url=None
        android_channel_id=None
        notification_setting="CMNTLIKE"

        notification_obj=Notification(user=notification_to, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)

        return CommentLikeMutation(new_commentlike)

class Momentcommentmutation(graphene.Mutation):
    class Arguments:
        # user=graphene.String(required=True)
        moment_id=graphene.ID()
        comment_description=graphene.String(required=True)
        reply_to=graphene.String(required=False)

    comment=graphene.Field(CommentType)

    @classmethod
    def mutate(cls,root,info,moment_id,comment_description, reply_to=None):
        user=info.context.user
        new_comment=Comment(user=user, momemt_id=moment_id,comment_description=comment_description, reply_to_id=reply_to)
        new_comment.save()
        
        notification_to=new_comment.momemt.user

        # TODO: set data payload, user avtar as icon
        data={}
        priority=None
        icon=None
        app_url=None
        android_channel_id=None
        notification_setting="CMNT"

        notification_obj=Notification(user=notification_to, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        
        return Momentcommentmutation(comment=new_comment)

class Momentreportmutation(graphene.Mutation):
    class Arguments:
        # user=graphene.String(required=True)
        moment_id=graphene.ID()
        Report_msg=graphene.String(required=True)

    report=graphene.Field(ReportType)

    @classmethod
    def mutate(cls,root,info,moment_id,Report_msg):
        user=info.context.user
        new_report=Report(user=user, momemt_id=moment_id,Report_msg=Report_msg )
        new_report.save()
        return Momentreportmutation(report=new_report)

class GenericCommentMutation(graphene.Mutation):
    generic_comment = graphene.Field(GenericCommentType)
    class Arguments:
        object_type=graphene.String()
        comment_description=graphene.String()
        object_id=graphene.Int()


    @classmethod
    def mutate(cls, root, info, object_type, object_id,comment_description):
        user = info.context.user
        content_type=ContentType.objects.get(app_label="moments", model=object_type)
        new_comment=GenericComment(user=user, comment_description=comment_description, content_type=content_type, object_id=object_id)
        new_comment.save()
        story=Story.objects.get(id=object_id)
        notification_to=story.user
        # TODO: set data payload, user avtar as icon

        data={
            'comment_comment_description':comment_description,
        }
        priority=None
        icon=None
        app_url=None
        android_channel_id=None
        notification_setting="CMNT"

        notification_obj=Notification(user=notification_to, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        return GenericCommentMutation(new_comment)

class GenericLikeMutation(graphene.Mutation):
    generic_like = graphene.Field(GenericLikeType)
    class Arguments:
        object_type=graphene.String()
        object_id=graphene.Int()


    @classmethod
    def mutate(cls, root, info, object_type, object_id):
        user = info.context.user
        content_type=ContentType.objects.get(app_label="moments", model=object_type)
        like=GenericLike.objects.filter(user=user, content_type=content_type, object_id=object_id)
        if like.exists():
            like=like[0]
            like.delete()
            return GenericLikeMutation(like)
        new_like=GenericLike(user=user, content_type=content_type, object_id=object_id)
        new_like.save()
        story=Story.objects.get(id=object_id)
        notification_to=story.user
        # TODO: set data payload, user avtar as icon
        data={
            "pk":story.id
        }
        priority=None
        icon=None
        app_url=None
        android_channel_id=None
        notification_setting="STLIKE"

        notification_obj=Notification(user=notification_to, sender=user, app_url=app_url, notification_setting_id=notification_setting, data=data,priority=priority)
        send_notification_fcm(notification_obj=notification_obj, android_channel_id=android_channel_id, icon=icon)
        return GenericLikeMutation(new_like)



class Mutation(graphene.ObjectType):
    insert_moment=Momentmutation.Field()
    insert_story=Storymutation.Field()
    delete_moment=Momentdeletemutation.Field()
    like_moment=Momentlikemutation.Field()
    comment_moment=Momentcommentmutation.Field()
    report_moment=Momentreportmutation.Field()
    like_comment=CommentLikeMutation.Field()
    generic_comment=GenericCommentMutation.Field()
    generic_like=GenericLikeMutation.Field()
    

class Query(graphene.ObjectType):

    # all_user_stories=DjangoFilterConnectionField(StoryType)
    # all_user_moments = DjangoFilterConnectionField(MomentsTyps)
    # all_user_comments = DjangoFilterConnectionField(CommentType)


    # def resolve_all_user_stories(root, info):
    #     return Story.objects.filter(created_date__gte=datetime.datetime.now()-datetime.timedelta(hours=EXPIRE_TIME)).order_by('-created_date','user')
        
    current_user_moments=graphene.List(MomentsTyps)
    all_moments=graphene.List(MomentsTyps)
    current_user_stories=graphene.List(StoryType)
    all_user_stories=DjangoFilterConnectionField(StoryType)
    all_comments = graphene.List(CommentType, moment_id=graphene.String(required=True))
    all_user_moments = DjangoFilterConnectionField(MomentsTyps)
    all_user_comments = DjangoFilterConnectionField(CommentType)

    def resolve_all_comments(self,info, **kwargs):
        momentId=kwargs.get('moment_id')
        return Comment.objects.filter(momemt_id=momentId, reply_to=None).order_by('-created_date')
        
    def resolve_all_moments(self, info):
        return Moment.objects.all().order_by('-created_date')

    # def resolve_all_user_stories(root, info):
    #     return Story.objects.filter(created_date__gte=datetime.datetime.now()-datetime.timedelta(hours=EXPIRE_TIME)).order_by('-created_date','user')
        
    def resolve_current_user_stories(root, info):
        
        user=info.context.user
        return Story.objects.filter(user=user, created_date__gte=datetime.datetime.now()-datetime.timedelta(seconds=EXPIRE_TIME)).order_by('-created_date')



    def resolve_current_user_moments(root,info):
        
        user = info.context.user
        return Moment.objects.filter(user=user).all().order_by("-created_date")
