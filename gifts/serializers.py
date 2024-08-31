from .models import Gift
from rest_framework.serializers import ModelSerializer

class GiftSerializer(ModelSerializer):
    class Meta:
        model = Gift
        fields = '__all__'