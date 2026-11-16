"""Project URL configuration: admin is built in; pages owns the public site URLs."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
]
