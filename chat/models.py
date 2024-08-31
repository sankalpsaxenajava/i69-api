from django.db import models
import time
from django.contrib.auth import get_user_model
from push_notifications.models import APNSDevice, GCMDevice


User = get_user_model()

class Room(models.Model):
    name = models.CharField(max_length=128)
    user_id = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="User1") #user 1
    target = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="User2") # user 2
    last_modified = models.DateTimeField(auto_now_add=False,blank=True,null=True)
    deleted = models.PositiveSmallIntegerField(default=0)
    # if None has deleted = 0
    # if user_id has deleted = 1
    # if target has deleted = 2
    # if delete gte 0 = deleet all message of the room;

    def __str__(self):
        return f'{self.name} ({self.user_id}: {self.target}) [{self.last_modified}]'


class Message(models.Model):
    room_id = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    user_id = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="Sender") #user 1
    content = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.DateTimeField(auto_now_add=False,blank=True,null=True)
    sender_worker=models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,related_name="sender_worker")
    receiver_worker=models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,related_name="receiver_worker")

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f'{self.user_id.username}: {self.content} [{self.timestamp}]'

class Notes(models.Model):
    room_id = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    content = models.CharField(max_length=5000, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    forRealUser = models.BooleanField(default=False)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f'{self.room_id}: {self.content} [{self.timestamp}]'


class Broadcast(models.Model):
    by_user_id = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="Create_By") #user 1
    content = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    deleted = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        #return f'{self.by_user_id.username}: {self.content} [{self.timestamp}]'
        return f'{self.content}'

class FirstMessage(models.Model):
    by_user_id = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name="FMCreate_By") #user 1
    content = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        #return f'{self.by_user_id.username}: {self.content} [{self.timestamp}]'
        return f'{self.content}'

def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.xlsx', '.xls', '.csv', '.txt', '.mp3', '.mp4', '.avi', '.mpg', '.mk4', '.wav', '.zip', '.rar']
    invalid_extensions = ['.exe', '.apk', '.htaccess', '.msi', '.env', '.gitignore']
    if ext.lower() in invalid_extensions:
        raise ValidationError('Unsupported file extension.')

def upload_location(instance, filename):
    filebase, extension = filename.rsplit('.', 1)
    return 'chat_files/%s_%s.%s' % (filebase,time.time(), extension)

class ChatMessageImages(models.Model):
    upload_type=models.CharField(max_length=100,null=True)
    image = models.FileField(upload_to=upload_location, validators=[validate_file_extension])

class NotificationSettings(models.Model):
    id = models.CharField(max_length=25, primary_key=True)
    title = models.CharField(max_length=50)
    message_str = models.CharField(max_length=70, null=True)

    def __str__(self):
        return self.id

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    priority = models.IntegerField(null=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    app_url = models.CharField(max_length=100, null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="notification_sender")
    seen = models.BooleanField(default=False)
    notification_setting = models.ForeignKey(NotificationSettings, on_delete=models.SET_NULL, null=True)
    notification_body = models.CharField(max_length=1000, null=True)
    data = models.CharField(max_length=500, null=True)


    def create_body(self):
        print('self here...', self.notification_setting)
        try:
            obj_ = NotificationSettings.objects.get(id=self.notification_setting)
            if self.sender:
                body=f"{self.sender.fullName} {obj_.message_str}"
            else:
                body=obj_.message_str
            return body
        except NotificationSettings.DoesNotExist:
            raise Exception("Notification ID not exists.")

def send_notification_fcm(notification_obj,android_channel_id=None, icon=None,image=None,**kwargs):
    
    user = notification_obj.user
    print("In send Notification FCM")
    body = notification_obj.create_body()
    print("Notification body created.")
    title = notification_obj.notification_setting.title
    print(f"send Notification FCM: {title}")
    data = notification_obj.data
    print(f"send Notification FCM: {data}")
    if notification_obj.notification_setting.id=="ADMIN":
        changed_coins=int(kwargs['coins'])
        
        if changed_coins<0:
            body=f"{notification_obj.sender.fullName} has deducted your {abs(changed_coins)} coins and now total coins are {kwargs['current_coins']}."
        else:
            body=f"{notification_obj.sender.fullName} has offered you {changed_coins} coins."

    print(f"send Notification FCM: Calling GCM")
    print(f"send Notification FCM body: {body}")

    fcm_devices = GCMDevice.objects.filter(user=user)
    print(f"FCM Devices: {fcm_devices}")
    print(f"FCM Devices body: {body}")
    if kwargs.get('message_count'):
        body = kwargs['message_count']

    # resp = fcm_devices.send_message(message={"title": title, "body": body}, badge=1, extra={"title": title, "icon": icon, "data":data,"image":image})
    resp = fcm_devices.send_message(body, badge=1, sound="default", extra={"title": title, "icon": icon,
                                                                           "data": data, "image": image})
    print(f"send Notification FCM: {resp}")
    notification_obj.notification_body=body
    notification_obj.save()
