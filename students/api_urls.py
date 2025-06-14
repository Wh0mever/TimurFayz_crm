from django.urls import path, include

from . import api_views

urlpatterns = [
    path(
        'students/', include([
            path(
                '',
                api_views.StudentViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.StudentViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            ),
            path(
                '<int:pk>/balance-report/',
                api_views.StudentViewSet.as_view(
                    {
                        'get': 'get_student_balance_report',
                    }
                )
            ),
            path(
                'create-options/',
                api_views.StudentViewSet.as_view(
                    {
                        'get': 'get_create_options',
                    }
                )
            ),
        ])
    ),
    path(
        'groups/', include([
            path(
                '',
                api_views.StudyGroupViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.StudyGroupViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            ),
            # path(
            #     '<int:pk>/study-days/',
            #     api_views.StudyGroupViewSet.as_view(
            #         {
            #             'post': 'add_study_day',
            #         }
            #     )
            # ),
            # path(
            #     '<int:pk>/study-days/<int:study_day_id>/',
            #     api_views.StudyGroupViewSet.as_view(
            #         {
            #             'delete': 'delete_study_day',
            #         }
            #     )
            # ),
            path(
                'create-options/',
                api_views.StudyGroupViewSet.as_view(
                    {
                        'get': 'get_create_options',
                    }
                )
            ),
        ])
    ),
    path(
        'balance-changes/', include([
            path(
                '',
                api_views.StudentBalanceAdjustmentViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.StudentBalanceAdjustmentViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            ),
        ])
    ),
    path(
        'transactions/', include([
            path(
                '',
                api_views.StudentTransactionViewSet.as_view(
                    {
                        'get': 'list',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.StudentTransactionViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'delete': 'destroy',
                    }
                )
            ),
        ])
    ),
    path(
        'student-bonuses/', include([
            path(
                '',
                api_views.StudentBonusViewSet.as_view(
                    {
                        'get': 'list',
                        'post': 'create',
                    }
                )
            ),
            path(
                '<int:pk>/',
                api_views.StudentBonusViewSet.as_view(
                    {
                        'get': 'retrieve',
                        'put': 'partial_update',
                        'delete': 'destroy',
                    }
                )
            ),
        ])
    ),
    path('send-sms-to-debtors/', api_views.SendSmsToDebtors.as_view())
    # path(
    #     'lessons/', include([
    #         path(
    #             '',
    #             api_views.StudyLessonViewSet.as_view(
    #                 {
    #                     'get': 'list',
    #                 }
    #             )
    #         ),
    #         path(
    #             '<int:pk>/',
    #             api_views.StudyLessonViewSet.as_view(
    #                 {
    #                     'get': 'retrieve',
    #                     'put': 'partial_update',
    #                 }
    #             )
    #         ),
    #     ])
    # ),
    # path(
    #     'student-visits/', include([
    #         path(
    #             '',
    #             api_views.StudentVisitView.as_view(
    #                 {
    #                     'get': 'list',
    #                     'post': 'create',
    #                 }
    #             )
    #         ),
    #         path(
    #             '<int:pk>/',
    #             api_views.StudentVisitView.as_view(
    #                 {
    #                     'get': 'retrieve',
    #                     'delete': 'destroy',
    #                 }
    #             )
    #         ),
    #     ])
    # ),
]
