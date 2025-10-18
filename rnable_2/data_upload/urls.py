from django.urls import path
from . import views

app_name = 'data_upload'

urlpatterns = [
    path('', views.single_upload, name='single_upload'),
]