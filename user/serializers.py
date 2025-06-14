from typing import Dict, Any

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password
from drf_extra_fields.fields import Base64ImageField
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import serializers
from base.serializers import DynamicFieldsModelSerializer
from user.models import Worker

User = get_user_model()


class UserSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'avatar', 'user_type', 'is_active', 'is_superuser')


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
        }
        user = User.objects.filter(**authenticate_kwargs).first()
        if user is None:
            raise AuthenticationFailed('User does not exist!')
        password = attrs['password']
        if not user.check_password(password):
            raise AuthenticationFailed('Incorrect password!')
        authenticate_kwargs['password'] = password

        self.user = authenticate(**authenticate_kwargs)

        if not self.user:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        data = super().validate(attrs)
        data['user_data'] = UserSerializer(user, context=self.context).data
        return data


class UserCreateSerializer(serializers.ModelSerializer):
    # password2 = serializers.CharField(max_length=128, write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password',  'user_type')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    # def validate(self, data):
    #     if data['password'] != data['password2']:
    #         raise serializers.ValidationError("Passwords dont match")
    #     return data

    def create(self, validated_data):
        # validated_data.pop('password2')
        validated_data['password'] = make_password(validated_data['password'])
        user = User.objects.create(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'avatar', 'user_type')

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'avatar':
                if not value or value == '' and instance.avatar:
                    continue
            setattr(instance, attr, value)

        instance.save()
        return instance


class UserChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, write_only=True)
    password2 = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data


class WorkerSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Worker
        fields = ('id', 'user', 'salary', 'department')


class WorkerCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()

    class Meta:
        model = Worker
        fields = ('id', 'user', 'salary', 'department')


    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserCreateSerializer().create(user_data)
        worker = Worker.objects.create(user=user, **validated_data)
        return worker


class WorkerUpdateSerializer(serializers.ModelSerializer):
    user = UserUpdateSerializer()

    class Meta:
        model = Worker
        fields = ('id', 'user', 'salary', 'department')

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        user = UserUpdateSerializer.update(UserUpdateSerializer(), instance=instance.user, validated_data=user_data)
        worker = super().update(instance, validated_data)
        worker.user = user
        return worker
