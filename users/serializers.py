from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'role', 'telephone', 'village', 'region']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model  = User
        fields = ['username', 'email', 'password', 'role', 'telephone', 'village', 'region']

    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data['username'],
            email    = validated_data.get('email', ''),
            password = validated_data['password'],
            role     = validated_data['role'],
            telephone = validated_data.get('telephone', ''),
            village  = validated_data.get('village', ''),
            region   = validated_data.get('region', ''),
        )
        return user