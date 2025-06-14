from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from user import api_views

urlpatterns = [
    # JWT Token
    path(
        "users/",
        include([
            # JWT Token
            path('login/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
            path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

            path(
                '',
                api_views.UserViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.UserViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                    }
                )
            ),
            path(
                '<int:pk>/password/',
                api_views.UserViewSet.as_view(
                    {
                        'put': 'change_password',
                    }
                )
            ),
            path(
                '<int:pk>/activate/',
                api_views.UserViewSet.as_view(
                    {
                        'put': 'activate_account',
                    }
                )
            ),
            path(
                '<int:pk>/deactivate/',
                api_views.UserViewSet.as_view(
                    {
                        'put': 'deactivate_account',
                    }
                )
            ),
        ])
    ),
    path(
        "users/me/",
        include([
            path(
                '',
                api_views.ActiveUserViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update'
                    }
                )
            ),
            path(
                'password/',
                api_views.ActiveUserViewSet.as_view(
                    {
                        'put': 'change_password'
                    }
                )
            ),
            path(
                'avatar/',
                api_views.ActiveUserViewSet.as_view(
                    {
                        'delete': 'remove_avatar'
                    }
                )
            ),
        ])
    ),
    path(
        'workers/',
        include([
            path(
                '',
                api_views.WorkerViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.WorkerViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                    }
                )
            ),
            path(
                '<int:pk>/password/',
                api_views.WorkerViewSet.as_view(
                    {
                        'put': 'change_password',
                    }
                )
            ),
            path(
                '<int:pk>/activate/',
                api_views.WorkerViewSet.as_view(
                    {
                        'put': 'activate_account',
                    }
                )
            ),
            path(
                '<int:pk>/deactivate/',
                api_views.WorkerViewSet.as_view(
                    {
                        'put': 'deactivate_account',
                    }
                )
            ),
        ])
    )
]
