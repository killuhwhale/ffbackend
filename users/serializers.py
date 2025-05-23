from django.contrib.auth.models import Group
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = get_user_model().USERNAME_FIELD


class UserCreateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['email', 'username', 'password', 'id', 'sub_end_date',]

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class UserSerializer(serializers.HyperlinkedModelSerializer):
    membership_on = serializers.SerializerMethodField()

    def get_membership_on(self, instance):
        return True

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'id',  'sub_end_date', 'customer_id', 'membership_on']


class UserWithoutEmailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'id']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']
