from django.db import models
from user.models import User
import uuid
import datetime
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation

# Create your models here.

class GenericLike(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="likes")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    user=models.ForeignKey(User, related_name="user_likes", on_delete=models.CASCADE)

class GenericComment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="comments")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    user=models.ForeignKey(User, related_name="user_comments", on_delete=models.CASCADE)
    comment_description=models.CharField(max_length=100, null=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True)


class Story(models.Model):
    
    def get_avatar_path(self, filename):
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return 'static/uploads/stories/' + filename
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    created_date=models.DateTimeField(auto_now_add=True)
    file=models.FileField(upload_to=get_avatar_path, max_length=1000)
    thumbnail=models.ImageField(upload_to=get_avatar_path, blank=True, null=True)
    likes = GenericRelation(GenericLike)
    comments = GenericRelation(GenericComment)
   

        


class Moment(models.Model):
    def get_avatar_path(self, filename):
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return 'static/uploads/moments/' + filename

    user=models.ForeignKey(User, related_name="User_for_moments", on_delete=models.CASCADE)
    Title=models.CharField(max_length=100,null=True)
    moment_description=models.TextField()
    created_date=models.DateTimeField(auto_now_add=True)
    file=models.FileField(upload_to=get_avatar_path, null=True, blank=True, max_length=1000)


    
    def __str__(self):
        return str(self.Title)



class Like(models.Model):
    user=models.ForeignKey(User, related_name="User_for_like", on_delete=models.CASCADE)
    momemt=models.ForeignKey(Moment , related_name="momemt_for_like", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

class Comment(models.Model):
    user=models.ForeignKey(User, related_name="User_for_comment", on_delete=models.CASCADE)
    comment_description=models.TextField()
    momemt=models.ForeignKey(Moment , related_name="momemt_for_comment", on_delete=models.CASCADE)
    created_date=models.DateTimeField(auto_now_add=True, null=True)
    reply_to=models.ForeignKey('self', related_name="parent_comment", null=True, blank=True, on_delete=models.CASCADE)



    def __str__(self):
        return str(self.id)

class CommentLike(models.Model):
    user=models.ForeignKey(User, related_name="likers", on_delete=models.CASCADE)
    comment=models.ForeignKey(Comment, on_delete=models.CASCADE)


class Report(models.Model):
    user=models.ForeignKey(User, related_name="User_for_report", on_delete=models.CASCADE)
    Report_msg=models.TextField()
    momemt=models.ForeignKey(Moment , related_name="momemt_for_report", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

class StoryVisibleTime(models.Model):
    text = models.CharField(" ", max_length=20, default="Click to change")
    weeks = models.IntegerField(default=0)
    days = models.IntegerField(default=3)
    hours = models.IntegerField(default=1)
    # hours = models.DecimalField(max_digits = 2,decimal_places = 2, null=True)

    def __str__(self):
        return str(self.weeks) + '-' + str(self.days) + '-' + str(self.hours)
