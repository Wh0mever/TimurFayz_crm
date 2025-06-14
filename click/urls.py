from django.urls import path

from click.views import TestView

urlpatterns = [
    path('click/transaction/', TestView.as_view())
]