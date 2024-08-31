from rest_framework import serializers
from .models import Purchase, User


class PurchaseSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    purchase_method = serializers.CharField(source="method")
    coins = serializers.IntegerField()
    money = serializers.DecimalField(max_digits = 5,decimal_places = 2)

    def create(self, validated_data):
        return Purchase(**validated_data)