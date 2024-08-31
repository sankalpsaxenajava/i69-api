from django.db import models
import uuid

from django.dispatch import receiver
from user.models import User

# Create your models here.
class Gift(models.Model):
    def get_avatar_path(self, filename):
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return 'static/uploads/gift/' + filename

    type_choice=(
        ("real","real_gift"),
        ("virtual","virtual_gift")
    )
    gift_name=models.CharField(max_length=100)
    cost=models.FloatField()
    picture=models.ImageField(upload_to=get_avatar_path,blank=True)
    type=models.CharField(choices=type_choice,max_length=7)
    
    

    def __str__(self):
        return self.gift_name

class Giftpurchase(models.Model):
    user=models.ForeignKey(User, verbose_name="Buyer", related_name="user_for_giftpurchase",on_delete=models.CASCADE)
    gift=models.ForeignKey(Gift, related_name="gift_for_giftpurchase",on_delete=models.CASCADE)
    receiver=models.ForeignKey(User, related_name="receiver_for_giftpurchase", on_delete=models.CASCADE, null=True)
    purchased_on=models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"id:{self.id} {self.gift} {self.user} for {self.receiver} on {self.purchased_on}"
