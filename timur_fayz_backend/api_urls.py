from django.urls import path, include

urlpatterns = [
    path('', include('user.api_urls')),
    path('', include('students.api_urls')),
    path('', include('payment.api_urls')),
    path('', include('payme.api_urls')),
    # path('', include('click.urls')),
]