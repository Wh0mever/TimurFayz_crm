from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework_simplejwt.views import TokenObtainPairView

from base.api_views import MultiSerializerViewSetMixin
from user.filters import WorkerFilter, UserFilter
from user.models import Worker
from user.serializers import CustomTokenObtainSerializer, UserSerializer, UserUpdateSerializer, \
    UserChangePasswordSerializer, UserCreateSerializer, WorkerSerializer, WorkerCreateSerializer, WorkerUpdateSerializer

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):

    @extend_schema(
        request=CustomTokenObtainSerializer,
        responses={
            200: CustomTokenObtainSerializer,
            401: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "string",
                            "example": "User does not exist"
                        }
                    }
                },
                description="Bad Request"
            )
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ActiveUserViewSet(MultiSerializerViewSetMixin, ViewSet):
    serializer_action_classes = {
        'retrieve': UserSerializer,
        'partial_update': UserUpdateSerializer,
        'change_password': UserChangePasswordSerializer,
    }

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer_class()(user, context={'request': request})
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer_class()(user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def change_password(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response({"message": "Успех"})

    def remove_avatar(self, request, *args, **kwargs):
        user = request.user
        user.avatar = None
        user.save()
        serializer = UserSerializer(instance=user)
        return Response(serializer.data)


class UserViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = User.objects.all()
    serializer_action_classes = {
        'list': UserSerializer,
        'retrieve': UserSerializer,
        'create': UserCreateSerializer,
        'partial_update': UserUpdateSerializer,
        'change_password': UserChangePasswordSerializer,
    }
    filter_backends = [
        SearchFilter,
        DjangoFilterBackend
    ]
    search_fields = [
        'first_name', 'last_name'
    ]
    filterset_class = UserFilter

    def change_password(self, request, *args, **kwargs):
        instance: User = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.set_password(serializer.validated_data['password'])
        instance.save()
        return Response({"response": "Успех"})

    def deactivate_account(self, request, pk):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(UserSerializer(instance=instance).data)

    def activate_account(self, request, pk):
        instance = self.get_object()
        instance.is_active = True
        instance.save()
        return Response(UserSerializer(instance=instance).data)


class WorkerViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Worker.objects.all()
    serializer_action_classes = {
        'list': WorkerSerializer,
        'retrieve': WorkerSerializer,
        'create': WorkerCreateSerializer,
        'partial_update': WorkerUpdateSerializer,
        'change_password': UserChangePasswordSerializer,
    }
    filter_backends = [
        SearchFilter,
        DjangoFilterBackend,
    ]
    search_fields = [
        'first_name', 'last_name'
    ]
    filterset_class = WorkerFilter

    def change_password(self, request, *args, **kwargs):
        instance: Worker = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.user.set_password(serializer.validated_data['password'])
        instance.user.save()
        return Response({"response": "Успех"})

    def deactivate_account(self, request, pk):
        instance = self.get_object()
        instance.user.is_active = False
        instance.user.save()
        return Response(WorkerSerializer(instance=instance).data)

    def activate_account(self, request, pk):
        instance = self.get_object()
        instance.user.is_active = True
        instance.user.save()
        return Response(WorkerSerializer(instance=instance).data)
