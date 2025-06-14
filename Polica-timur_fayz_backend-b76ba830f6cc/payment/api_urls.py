from django.urls import path, include

from . import api_views

urlpatterns = [
    path(
        'outlay-categories/', include([
            path(
                '',
                api_views.OutlayCategoryViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.OutlayCategoryViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            )
        ])
    ),
    path(
        'outlay-items/', include([
            path(
                '',
                api_views.OutlayItemViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.OutlayItemViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            )
        ])
    ),
    path(
        'cashiers/', include([
            path(
                '',
                api_views.CashViewSet.as_view(
                    {
                        'get': 'list',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.CashViewSet.as_view(
                    {
                        'get': 'retrieve',
                    }
                )
            )
        ])
    ),
    path(
        'payments/', include([
            path(
                '',
                api_views.PaymentViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.PaymentViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            ),
            path(
                'summary/',
                api_views.PaymentViewSet.as_view(
                    {
                        'get': 'get_summary',
                    }
                )
            ),
        ])
    ),
]
