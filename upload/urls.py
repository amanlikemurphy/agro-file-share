from django.urls import path
from . import views
from .views import generate_sas_link

urlpatterns = [
    path('', views.upload_file, name='upload_file'),
]
