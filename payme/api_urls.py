from django.urls import path

from .views import PaymeCallbackView

urlpatterns = [
    path('payme/merchant/', PaymeCallbackView.as_view()),
]